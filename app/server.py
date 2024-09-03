import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from app.auth.routes import router as auth_routes
from app.chatbot.routes import router as chatbot_routes
from app.file_upload.routes import router as file_upload_routes

app = FastAPI(
    title="Chatbot API",
    description="A simple chatbot API with Langchain and FastAPI",
    version="1.0.0",
)
app.include_router(auth_routes, prefix="/api/v1")
app.include_router(chatbot_routes, prefix="/api/v1")
app.include_router(file_upload_routes, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
