import uuid
import logging
from sqlalchemy.orm import Session
from app.db.models import ChatSession, ChatMessage, MessageRole, LeadState
from app.services.state_service import StateService
from app.services.search_service import SearchService
from app.llm.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

OFF_SCRIPT_TRIGGERS = [
    "who created you",
    "who made you",
    "what is your name",
    "who are you",
    "what can you do",
    "how can you help",
    "what do you do",
    "tell me about yourself",
    "are you a bot",
    "are you ai",
    "are you human",
    "your name",
    "about you",
    "what are you",
]


class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = GroqProvider()
        self.state_service = StateService(db)
        self.search_service = SearchService()

    async def reply(self, session_id: uuid.UUID, user_message: str) -> dict:
        # 1. Retrieve the active session
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            raise ValueError("Session not found. Please start a new chat.")

        # 2. Persist the User's Message
        user_msg = ChatMessage(
            session_id=session.id,
            role=MessageRole.USER,
            content=user_message
        )
        self.db.add(user_msg)

        # Snapshot the state BEFORE we process the message
        initial_state = session.lead_state

        # 3. Run the State Machine
        try:
            state_result = await self.state_service.process_state(session, user_message)
        except Exception as e:
            logger.exception("State machine failed for session %s", session_id)
            self.db.rollback()
            raise ValueError(f"State processing error: {str(e)}")

        prompt_append = state_result.get("append", "")
        is_pricing_intent = state_result.get("pricing_intent", False)

        final_answer = ""
        sources = []

        # 4. Detect off-script questions (identity / capabilities) at ANY state
        is_off_script = any(
            trigger in user_message.lower() for trigger in OFF_SCRIPT_TRIGGERS
        )

        if is_off_script:
            logger.info("Off-script input detected for session %s", session_id)
            off_script_reply = (
                "I'm MoinSystem AI, a virtual assistant created by MoinSystems to help you "
                "explore our software solutions and services. I'd love to learn more about "
                "your needs so we can help you better!"
            )
            final_answer = off_script_reply
            if prompt_append:
                final_answer += f"\n\n{prompt_append}"

        # 5. Answer-First Behavior — only when session was in NORMAL state
        elif initial_state == LeadState.NORMAL:  # type: ignore

            # Pricing intent: never quote a price, transition to lead capture
            if is_pricing_intent:
                logger.info("Pricing intent detected for session %s", session_id)
                final_answer = (
                    "Pricing varies depending on the scope, features, and specific requirements "
                    "of your project. We build tailored solutions to match your needs.\n\n"
                    f"{prompt_append}"
                )

            # All other questions: use RAG + LLM
            else:
                try:
                    retrieved_context = self.search_service.search(user_message)

                    system_prompt = (
                        "You are an expert, professional AI sales assistant for MoinSystems. "
                        "MoinSystems is a software company that builds tailored digital solutions "
                        "including web apps, mobile apps, AI integrations, and enterprise software. "
                        "Answer the user's question concisely based on the provided context. "
                        "Keep your response strictly under 2 short paragraphs. "
                        "Do not invent or assume information not present in the context. "
                        "If the context does not contain a relevant answer, say so politely."
                    )

                    combined_prompt = (
                        f"Context:\n{retrieved_context}\n\n"
                        f"User Question: {user_message}"
                    )

                    core_answer = await self.llm.generate_response(
                        system_instruction=system_prompt,
                        user_prompt=combined_prompt
                    )

                    final_answer = core_answer
                    if prompt_append:
                        final_answer += f"\n\n{prompt_append}"

                except Exception as e:
                    logger.exception(
                        "RAG/LLM generation failed for session %s: %s", session_id, str(e)
                    )
                    # Graceful fallback — never return a 500 to the user
                    final_answer = (
                        "I'm sorry, I had trouble retrieving information for that. "
                        "Could you try rephrasing your question?"
                    )
                    if prompt_append:
                        final_answer += f"\n\n{prompt_append}"

        # 6. Lead capture states (COLLECTING_NAME, COLLECTING_EMAIL, COLLECTING_PHONE, etc.)
        else:
            # State machine already validated the input and produced the next prompt.
            # No RAG needed — just return the scripted next step.
            logger.info(
                "Lead capture state %s for session %s", session.lead_state, session_id
            )
            final_answer = prompt_append

        # 7. Persist the Assistant's Message
        assistant_msg = ChatMessage(
            session_id=session.id,
            role=MessageRole.ASSISTANT,
            content=final_answer
        )
        self.db.add(assistant_msg)

        try:
            self.db.commit()
        except Exception as e:
            logger.exception("DB commit failed for session %s", session_id)
            self.db.rollback()
            raise ValueError(f"Failed to save message: {str(e)}")

        return {
            "answer": final_answer,
            "sources": sources
        }