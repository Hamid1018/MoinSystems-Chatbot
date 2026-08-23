import uuid
from sqlalchemy.orm import Session
from app.db.models import ChatSession, ChatMessage, MessageRole, LeadState
from app.services.state_service import StateService
from app.services.search_service import SearchService
from app.llm.groq_provider import GroqProvider

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
        user_msg = ChatMessage(session_id=session.id, role=MessageRole.USER, content=user_message)
        self.db.add(user_msg)
        
        # Snapshot the state BEFORE we process the message
        initial_state = session.lead_state
        
        # 3. Run the State Machine
        state_result = await self.state_service.process_state(session, user_message)
        prompt_append = state_result["append"]

        final_answer = ""
        sources = []

        # 4. Answer-First Behavior (5.5 & 5.6)
        if initial_state == LeadState.NORMAL:  # type: ignore
            
            # STRICT REQUIREMENT: If pricing intent was detected, NEVER invent/quote a price.
            # Completely skip the RAG search and LLM generation.
            if session.lead_state == LeadState.COLLECTING_NAME:  # type: ignore
                final_answer = (
                    "Pricing can vary widely depending on the scope, features, and specific "
                    "requirements of your project. We build tailored solutions to match your needs.\n\n"
                    f"{prompt_append}"
                )
            
            # For all other NON-pricing questions, use the RAG Search
            else:
                retrieved_context = self.search_service.search(user_message)
                
                system_prompt = (
                    "You are an expert, professional AI sales assistant for MoinSystem. "
                    "Answer the user's question concisely based on the provided context. "
                    "Keep your response strictly under 2 short paragraphs."
                )
                
                combined_prompt = f"Context:\n{retrieved_context}\n\nUser Question: {user_message}"
                
                core_answer = await self.llm.generate_response(
                    system_instruction=system_prompt,
                    user_prompt=combined_prompt
                )
                
                final_answer = core_answer
                if prompt_append:
                    final_answer += f"\n\n{prompt_append}"
                    
        else:
            # If we are already actively collecting data (name, email, etc.), skip RAG entirely
            final_answer = prompt_append

        # 5. Persist the Assistant's Message
        assistant_msg = ChatMessage(session_id=session.id, role=MessageRole.ASSISTANT, content=final_answer)
        self.db.add(assistant_msg)
        self.db.commit()

        return {
            "answer": final_answer,
            "sources": sources
        }