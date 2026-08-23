import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
from sqlalchemy.orm import declarative_base

Base = declarative_base()



class LeadState(PyEnum):
    NORMAL = "normal"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_EMAIL = "collecting_email"
    COLLECTING_PHONE = "collecting_phone"
    COMPLETED = "completed"

class MessageRole(PyEnum):
    USER = "user"
    ASSISTANT = "assistant"

class ChatSession(Base):
    __tablename__ = "chat_session"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_state = Column(Enum(LeadState), default=LeadState.NORMAL, nullable=False)
    
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    contact_number = Column(String(50), nullable=True)
    
    company_name = Column(String(255), nullable=True)
    project_summary = Column(Text, nullable=True)
    service_interest = Column(String(255), nullable=True)
    timeline = Column(String(255), nullable=True)
    budget_range = Column(String(255), nullable=True)
    source_page = Column(String(255), nullable=True)
    conversation_summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    delivery_status = Column(String(50), default="pending")
    provider_message_id = Column(String(255), nullable=True)
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_message"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_session.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
    
    
from pgvector.sqlalchemy import Vector  # Ensure this import is at the top of your models.py

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunk"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)  # Added 384-dimension vector column
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)