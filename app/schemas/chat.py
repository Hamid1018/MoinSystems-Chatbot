from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="User question or prompt")
    session_id: Optional[str] = Field(None, description="Optional session/conversation identifier")

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Assistant generated response")
    sources: List[str] = Field(default_factory=list, description="Knowledge chunk IDs referenced")