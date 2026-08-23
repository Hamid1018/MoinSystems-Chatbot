from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db
from app.db.models import ChatSession, LeadState
from app.schemas.lead import SessionCreateResponse, LeadCaptureRequest

router = APIRouter(tags=["Sessions & Leads"])

@router.post("/sessions", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_session(db: Session = Depends(get_db)):
    """Creates a new chat session and returns the UUID."""
    new_session = ChatSession()
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return SessionCreateResponse(session_id=new_session.id) # type: ignore

@router.post("/lead-capture", status_code=status.HTTP_200_OK)
def submit_lead_directly(payload: LeadCaptureRequest, db: Session = Depends(get_db)):
    """Allows standard web forms to bypass the chat and submit lead data directly."""
    session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    if payload.full_name:
        session.full_name = payload.full_name  # type: ignore
    if payload.email:
        session.email = payload.email  # type: ignore
    if payload.contact_number:
        session.contact_number = payload.contact_number  # type: ignore
        
    session.lead_state = LeadState.COMPLETED  # type: ignore
    db.commit()
    return {"message": "Lead captured successfully."}