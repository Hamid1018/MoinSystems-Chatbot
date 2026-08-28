import logging
from sqlalchemy.orm import Session
from pydantic import EmailStr, TypeAdapter
from app.db.models import ChatSession, LeadState
from app.llm.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

# ✅ Valid Groq models — pick one:
# "llama3-8b-8192"      — fastest, cheapest
# "llama3-70b-8192"     — smarter, slower
# "mixtral-8x7b-32768"  — good balance
GROQ_MODEL = "llama3-8b-8192"


class StateService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = GroqProvider()
        self.llm.model_name = GROQ_MODEL  # ✅ valid Groq model, not openai/gpt-oss-20b

    async def detect_intent(self, user_message: str) -> bool:
        """Determines if the user is asking a pricing/quote question."""
        system_prompt = (
            "Determine if the user is asking about pricing, costs, estimates, or quotes. "
            "Respond with ONLY 'True' or 'False'."
        )
        try:
            response = await self.llm.generate_response(
                system_instruction=system_prompt,
                user_prompt=user_message
            )
            return "true" in response.lower()
        except Exception as e:
            logger.exception("detect_intent failed: %s", str(e))
            return False  # safe default — don't crash the flow

    async def extract_lead_data(self, user_message: str, data_type: str) -> str:
        """Extracts specific entities (name, email, phone) from user messages."""
        system_prompt = (
            f"Extract the {data_type} from the user's message. "
            "Return ONLY the extracted value as a plain string. "
            "If no valid value is found, return the exact word 'None'."
        )
        try:
            response = await self.llm.generate_response(
                system_instruction=system_prompt,
                user_prompt=user_message
            )
            return response.strip()
        except Exception as e:
            logger.exception("extract_lead_data failed for %s: %s", data_type, str(e))
            return "None"  # safe default

    async def process_state(self, session: ChatSession, user_message: str) -> dict:
        """Runs the state machine to handle lead capture transitions."""

        # 1. Normal State — detect pricing intent
        if session.lead_state == LeadState.NORMAL:  # type: ignore
            is_pricing_intent = await self.detect_intent(user_message)
            if is_pricing_intent:
                session.lead_state = LeadState.COLLECTING_NAME  # type: ignore
                self.db.commit()
                return {
                    "append": "To give you an accurate estimate, may I please have your full name?",
                    "state": session.lead_state,
                    "pricing_intent": True,  # ← chat_service reads this
                }
            return {
                "append": "",
                "state": session.lead_state,
                "pricing_intent": False,
            }

        # 2. Collecting Name
        elif session.lead_state == LeadState.COLLECTING_NAME:  # type: ignore
            extracted_name = await self.extract_lead_data(user_message, "full name")

            if not extracted_name or extracted_name.lower() in ["none", "unknown", "null"]:
                return {
                    "append": "I didn't quite catch that. Could you please share your full name?",
                    "state": session.lead_state,
                    "pricing_intent": False,
                }

            session.full_name = extracted_name  # type: ignore
            session.lead_state = LeadState.COLLECTING_EMAIL  # type: ignore
            self.db.commit()

            return {
                "append": f"Thank you, {session.full_name}. What is the best email address to reach you at?",
                "state": session.lead_state,
                "pricing_intent": False,
            }

        # 3. Collecting Email
        elif session.lead_state == LeadState.COLLECTING_EMAIL:  # type: ignore
            extracted_email = await self.extract_lead_data(user_message, "email address")

            try:
                email_adapter = TypeAdapter(EmailStr)
                validated_email = email_adapter.validate_python(extracted_email)
                session.email = str(validated_email)  # type: ignore
                session.lead_state = LeadState.COLLECTING_PHONE  # type: ignore
                self.db.commit()

                return {
                    "append": "Great! Finally, what is the best phone number to reach you at?",
                    "state": session.lead_state,
                    "pricing_intent": False,
                }
            except Exception:
                return {
                    "append": "That email doesn't look quite right. Could you please provide a valid email address?",
                    "state": session.lead_state,
                    "pricing_intent": False,
                }

        # 4. Collecting Phone
        elif session.lead_state == LeadState.COLLECTING_PHONE:  # type: ignore
            extracted_phone = await self.extract_lead_data(user_message, "phone number")

            if not extracted_phone or extracted_phone.lower() in ["none", "unknown", "null"]:
                return {
                    "append": "I didn't catch a valid phone number. Could you please share it?",
                    "state": session.lead_state,
                    "pricing_intent": False,
                }

            # ✅ CRITICAL FIX: Save phone + state to DB FIRST, BEFORE sending email.
            # This ensures DB is never rolled back due to an email failure.
            session.contact_number = extracted_phone  # type: ignore
            session.lead_state = LeadState.COMPLETED  # type: ignore
            session.delivery_status = "pending"  # type: ignore

            try:
                self.db.commit()  # ✅ Commit lead data independently of email
            except Exception as e:
                logger.exception("Failed to save phone number for session %s", session.id)
                self.db.rollback()
                return {
                    "append": "Sorry, we had a technical issue saving your details. Please try again.",
                    "state": session.lead_state,
                    "pricing_intent": False,
                }

            # ✅ Now send email — failure here will NOT roll back the saved lead
            from app.services.email_service import EmailService
            email_service = EmailService()
            try:
                message_id = await email_service.send_lead_notification(session)
                session.delivery_status = "delivered"  # type: ignore
                session.provider_message_id = message_id  # type: ignore
                self.db.commit()  # update delivery status only
                prompt_append = (
                    "Thank you so much! Our team has been notified and will reach out to you shortly."
                )
            except Exception as e:
                logger.error(
                    "Failed to send lead email for session %s: %s", session.id, str(e)
                )
                # ✅ Mark as failed but lead data is already safely saved above
                try:
                    session.delivery_status = "failed"  # type: ignore
                    self.db.commit()
                except Exception:
                    self.db.rollback()

                prompt_append = (
                    "Thank you! We have your details saved. "
                    "Our team will review your info and reach out to you soon."
                )

            return {
                "append": prompt_append,
                "state": session.lead_state,
                "pricing_intent": False,
            }

        # 5. Completed State
        elif session.lead_state == LeadState.COMPLETED:  # type: ignore
            return {
                "append": "Is there anything else I can help you with?",
                "state": session.lead_state,
                "pricing_intent": False,
            }

        # Fallback
        return {
            "append": "",
            "state": session.lead_state,
            "pricing_intent": False,
        }