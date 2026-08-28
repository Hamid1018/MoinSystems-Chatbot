import os
import logging
import asyncio
import resend
from app.db.models import ChatSession

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        api_key = os.getenv("RESEND_API_KEY")  # ✅ Railway injects env vars directly
        if not api_key:
            logger.error("RESEND_API_KEY is not set in environment variables!")
            raise RuntimeError("RESEND_API_KEY is missing. Set it in Railway Variables.")
        resend.api_key = api_key

    async def send_lead_notification(self, session: ChatSession) -> str:
        """Send lead notification email via Resend."""
        html_payload = f"""
        <h2>New Lead Submission</h2>
        <ul>
            <li><strong>Name:</strong> {session.full_name}</li>
            <li><strong>Email:</strong> {session.email}</li>
            <li><strong>Phone:</strong> {session.contact_number}</li>
            <li><strong>Session ID:</strong> {session.id}</li>
        </ul>
        """

        params: resend.Emails.SendParams = {
            "from": "onboarding@resend.dev",
            "to": ["hamidnazir778@gmail.com"],
            "subject": f"New Lead: {session.full_name}",
            "html": html_payload,
        }

        # ✅ resend.Emails.send() is synchronous — run it in a thread pool
        # so it doesn't block the async event loop
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,  # uses default ThreadPoolExecutor
                lambda: resend.Emails.send(params)
            )
            message_id = response["id"]
            logger.info("Lead email sent successfully. Message ID: %s", message_id)
            return message_id

        except Exception as e:
            logger.error("Resend API error: %s", str(e))
            raise  # re-raise so state_service can handle it gracefully