
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



# 2. Register the router with the FastAPI app
app.include_router(chat_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1/sessions")


import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# --- Add this near the bottom of app/main.py (after your API routers) ---

DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "chat-widget", "dist")

if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_root():
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Do not catch API routes
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            return None
        file_path = os.path.join(DIST_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))