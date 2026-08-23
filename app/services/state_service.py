from sqlalchemy.orm import Session
from pydantic import EmailStr, TypeAdapter
from app.db.models import ChatSession, LeadState
from app.llm.groq_provider import GroqProvider

class StateService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = GroqProvider()
        # Ensure we are using an active production model on Groq
        self.llm.model_name = "openai/gpt-oss-20b"

    async def detect_intent(self, user_message: str) -> bool:
        """Determines if the user is asking a pricing/quote question."""
        system_prompt = (
            "Determine if the user is asking about pricing, costs, estimates, or quotes. "
            "Respond with ONLY 'True' or 'False'."
        )
        response = await self.llm.generate_response(
            system_instruction=system_prompt,
            user_prompt=user_message
        )
        return "true" in response.lower()

    async def extract_lead_data(self, user_message: str, data_type: str) -> str:
        """Extracts specific entities (name, email, phone) from user messages."""
        system_prompt = (
            f"Extract the {data_type} from the user's message. "
            "Return ONLY the extracted value as a plain string. "
            "If no valid value is found, return the exact word 'None'."
        )
        response = await self.llm.generate_response(
            system_instruction=system_prompt,
            user_prompt=user_message
        )
        return response.strip()

    async def process_state(self, session: ChatSession, user_message: str) -> dict:
        """Runs the state machine to handle lead capture transitions."""
        
        # 1. Handle Normal State
        if session.lead_state == LeadState.NORMAL:  # type: ignore
            is_pricing_intent = await self.detect_intent(user_message)
            if is_pricing_intent:
                session.lead_state = LeadState.COLLECTING_NAME  # type: ignore
                self.db.commit()
                return {
                    "append": "To give you an accurate estimate, may I please have your full name?",
                    "state": session.lead_state
                }
            return {"append": "", "state": session.lead_state}

        # 2. Handle Name Collection
        elif session.lead_state == LeadState.COLLECTING_NAME:  # type: ignore
            extracted_name = await self.extract_lead_data(user_message, "full name")
            
            # Prevent empty or failed extractions from breaking the flow
            if not extracted_name or extracted_name.lower() in ["none", "unknown", "null"]:
                return {
                    "append": "I didn't quite catch that. Could you please share your full name?", 
                    "state": session.lead_state
                }
                
            session.full_name = extracted_name  # type: ignore
            session.lead_state = LeadState.COLLECTING_EMAIL  # type: ignore
            prompt_append = f"Thank you, {session.full_name}. What is the best email address to reach you at?"
            
            self.db.commit()
            return {"append": prompt_append, "state": session.lead_state}

        # 3. Handle Email Collection
        elif session.lead_state == LeadState.COLLECTING_EMAIL:  # type: ignore
            extracted_email = await self.extract_lead_data(user_message, "email address")
            try:
                # Direct validation check using pydantic's email validator
                email_adapter = TypeAdapter(EmailStr)
                validated_email = email_adapter.validate_python(extracted_email)
                
                session.email = str(validated_email)  # type: ignore
                session.lead_state = LeadState.COLLECTING_PHONE  # type: ignore
                prompt_append = "Great! Finally, what is the best phone number to reach you at?"
            except Exception:
                prompt_append = "That email doesn't look quite right. Could you please provide a valid email address?"
                return {"append": prompt_append, "state": session.lead_state}
            
            self.db.commit()
            return {"append": prompt_append, "state": session.lead_state}

        # 4. Handle Phone Collection
      # 4. Handle Phone Collection
        elif session.lead_state == LeadState.COLLECTING_PHONE:  # type: ignore
            extracted_phone = await self.extract_lead_data(user_message, "phone number")
            
            if not extracted_phone or extracted_phone.lower() in ["none", "unknown", "null"]:
                return {"append": "I didn't catch a valid phone number. Could you please share it?", "state": session.lead_state}

            session.contact_number = extracted_phone  # type: ignore
            session.lead_state = LeadState.COMPLETED  # type: ignore
            
            # --- EMAIL INTEGRATION & FALSE-SUCCESS PREVENTION ---
            from app.services.email_service import EmailService
            import logging
            
            email_service = EmailService()
            try:
                message_id = await email_service.send_lead_notification(session)
                session.delivery_status = "delivered" # type: ignore
                session.provider_message_id = message_id # type: ignore
                prompt_append = "Thank you so much! Our team has been notified and will reach out to you shortly."
            except Exception as e:
                logging.error(f"Failed to send email for session {session.id}: {str(e)}")
                session.delivery_status = "failed" # type: ignore
                prompt_append = "Thank you! We have your details, but our notification system is delayed. We will review your info soon!"
            # ----------------------------------------------------
            
            self.db.commit()
            return {"append": prompt_append, "state": session.lead_state}

        # 5. Handle Completed State
        elif session.lead_state == LeadState.COMPLETED:  # type: ignore
            return {"append": "", "state": session.lead_state}

        return {"append": "", "state": session.lead_state}