import os
import resend
import logging
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from app.db.models import ChatSession

# 1. FORCE Python to read your .env file
load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # This will now successfully grab your API key!
        resend.api_key = os.getenv("RESEND_API_KEY") 
        
        if not resend.api_key:
            logger.error("CRITICAL ERROR: Resend API Key is missing! Check your .env file.")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def send_lead_notification(self, session: ChatSession) -> str:
        html_payload = f"""
        <h2>New Lead Submission</h2>
        <ul>
            <li><strong>Name:</strong> {session.full_name}</li>
            <li><strong>Email:</strong> {session.email}</li>
            <li><strong>Phone:</strong> {session.contact_number}</li>
            <li><strong>Session ID:</strong> {session.id}</li>
        </ul>
        """
        
        params = {
            "from": "onboarding@resend.dev", 
            "to": ["hamidnazir778@gmail.com"], 
            "subject": f"New Lead: {session.full_name}",
            "html": html_payload,
        }
        
        try:
            response = resend.Emails.send(params)  # type: ignore
            logger.info(f"Email sent successfully. Message ID: {response['id']}")
            return response["id"]
        except Exception as e:
            # 2. If it fails, print the EXACT error from Resend to the terminal
            logger.error(f"RESEND API ERROR: {str(e)}")
            raise e