
from fastapi.middleware.cors import CORSMiddleware

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.v1.chat import router as chat_router


# 1. Import the chat router you created

from app.api.v1.sessions import router as sessions_router



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="MoinSystems AI Chatbot API",
    description="Backend API for the MoinSystems AI Public Chatbot",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # type: ignore

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://moinsystemsai.com", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
   allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}

@app.get("/", tags=["default"])
def root():
    return {"message": "Welcome to the API"}

# 2. Register the router with the FastAPI app
app.include_router(chat_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")