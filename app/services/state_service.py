import os
import logging
import traceback
from sqlalchemy.orm import Session
from pydantic import EmailStr, TypeAdapter
from app.db.models import ChatSession, LeadState
from app.llm.groq_provider import GroqProvider
logger = logging.getLogger(__name__)

GROQ_MODEL = "llama3-8b-8192"


class StateService:
    def init(self, db: Session):
        self.db = db
        self.llm = GroqProvider()
        self.llm.model_name = GROQ_MODEL

    async def detect_intent(self, user_message: str) -> bool:
        """Determines if the user is asking a pricing/quote question."""
        # Keyword-based detection — fast and reliable
        pricing_keywords = [
            "how much", "price", "pricing", "cost", "costs", "quote",
            "estimate", "budget", "rates", "fee", "fees", "charge",
            "charges", "affordable", "expensive", "cheap", "package",
            "packages", "plan", "plans", "hire", "start", "begin",
            "get started", "i want to build", "can you develop",
            "i need a developer", "can you build", "build for me",
            "i want to hire", "can you make", "can you create"
        ]
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in pricing_keywords)

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
            return "None"

    async def process_state(self, session: ChatSession, user_message: str) -> dict:
        """Runs the state machine to handle lead capture transitions."""

        # 1. Normal State
        if session.lead_state == LeadState.NORMAL:  # type: ignore
            is_pricing_intent = await self.detect_intent(user_message)
            if is_pricing_intent:
                session.lead_state = LeadState.COLLECTING_NAME  # type: ignore
                self.db.commit()
                return {
                    "append": "To give you an accurate estimate, may I please have your full name?",
                    "state": session.lead_state,
                    "pricing_intent": True,
                }
            return {
                "append": "",
                "state": session.lead_state,
                "pricing_intent": False,
            }

        # 2. Collecting Name
        elif session.lead_state == LeadState.COLLECTING_NAME:  # type: ignore
            extracted_name = await self.extract_lead_data(user_message, "full name")
            logger.info("Extracted name: '%s'", extracted_name)

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
            logger.info("Extracted email: '%s'", extracted_email)

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
            logger.info("Extracted phone: '%s'", extracted_phone)

            if not extracted_phone or extracted_phone.lower() in ["none", "unknown", "null"]:
                return {
                    "append": "I didn't catch a valid phone number. Could you please share it?",
                    "state": session.lead_state,
                    "pricing_intent": False,
                }

            # ✅ STEP 1: Save lead data FIRST before anything else
            session.contact_number = extracted_phone  # type: ignore
            session.lead_state = LeadState.COMPLETED  # type: ignore
            session.delivery_status = "pending"  # type: ignore

            try:
                self.db.commit()
                logger.info("Lead data committed to DB for session %s", session.id)
            except Exception as e:
                logger.error("FULL TRACEBACK:\n%s", traceback.format_exc())
                self.db.rollback()
                return {
                    "append": "Sorry, we had a technical issue saving your details. Please try again.",
                    "state": session.lead_state,
                    "pricing_intent": False,
                }

            # ✅ STEP 2: Send email AFTER commit — failure won't roll back lead data
            logger.info(
                "Attempting email send. RESEND_API_KEY present: %s",
                bool(os.getenv("RESEND_API_KEY"))
            )

            from app.services.email_service import EmailService
            prompt_append = ""

            try:
                email_service = EmailService()
                logger.info("EmailService initialized successfully")

                message_id = await email_service.send_lead_notification(session)
                logger.info("Email sent successfully. Message ID: %s", message_id)

                session.delivery_status = "delivered"  # type: ignore
                session.provider_message_id = message_id  # type: ignore

                try:
                    self.db.commit()
                except Exception:
                    logger.warning("Could not update delivery_status to delivered — non-critical")
                    self.db.rollback()

                prompt_append = (
                    "Thank you so much! Our team has been notified and will reach out to you shortly."
                )

            except RuntimeError as e:
                # RESEND_API_KEY missing — raised by EmailService.__init__()
                logger.error("EmailService init failed (missing API key?): %s", str(e))
                logger.error("FULL TRACEBACK:\n%s", traceback.format_exc())

                try:
                    session.delivery_status = "failed"  # type: ignore
                    self.db.commit()
                except Exception:
                    self.db.rollback()

                prompt_append = (
                    "Thank you! We have your details saved. "
                    "Our team will review your info and reach out to you soon."
                )

            except Exception as e:
                # Resend API call failed
                logger.error("Email send failed: %s", str(e))
                logger.error("FULL TRACEBACK:\n%s", traceback.format_exc())

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