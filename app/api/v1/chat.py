import uuid
from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import traceback
from app.api.v1.deps import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/")
@limiter.limit("5/minute")
async def send_message(request: Request, payload: ChatRequest, db: Session = Depends(get_db)):
    
    if not payload.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A valid session_id is required to send messages."
        )
        
    chat_service = ChatService(db)
    
    try:
        # Convert string to UUID for the database
        session_uuid = uuid.UUID(payload.session_id)
        response = await chat_service.reply(session_uuid, payload.message)
        
        return ChatResponse(
            answer=response["answer"],
            sources=response["sources"]
        )
    except ValueError as ve:
        # Handles UUID parsing errors or missing session errors
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat generation failed: {str(e)}"
        )