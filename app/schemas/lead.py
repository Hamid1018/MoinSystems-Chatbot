import re
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from uuid import UUID

class SessionCreateResponse(BaseModel):
    session_id: UUID
    message: str = "Session created successfully."

class LeadCaptureRequest(BaseModel):
    session_id: UUID
    
    # Required Fields (marked as Optional here so the state machine can collect them one by one)
    full_name: Optional[str] = Field(None, description="Visitor's full name")
    email: Optional[EmailStr] = Field(None, description="Visitor's email address")
    contact_number: Optional[str] = Field(None, description="Visitor's phone number")
    
    # Optional Fields
    company_name: Optional[str] = Field(None)
    project_summary: Optional[str] = Field(None)
    service_interest: Optional[str] = Field(None)
    timeline: Optional[str] = Field(None)
    budget_range: Optional[str] = Field(None)
    source_page: Optional[str] = Field(None)

    @field_validator('full_name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            # Reject obviously invalid placeholders
            if len(v) < 2 or v.lower() in ["na", "n/a", "test", "unknown", "none"]:
                raise ValueError("Please provide a valid full name.")
        return v

    @field_validator('contact_number')
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            # Strip spaces, dashes, and parentheses for validation
            cleaned = re.sub(r'[\s\-\(\)]', '', v)
            # Ensure it contains at least 10 digits and optional leading '+'
            if not re.match(r'^\+?\d{10,15}$', cleaned):
                raise ValueError("Please provide a valid phone number containing 10 to 15 digits.")
        return v