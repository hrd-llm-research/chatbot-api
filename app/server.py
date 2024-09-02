import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from app.auth.routes import router as auth_routes
from app.chatbot.routes import router as chatbot_routes
from app.chat_with_llm.routes import llm, prompt
from app.file_upload.routes import router as file_upload_routes
from langchain_postgres import PostgresChatMessageHistory

app = FastAPI(
    title="Chatbot API",
    description="A simple chatbot API with Langchain and FastAPI",
    version="1.0.0",
)
app.include_router(auth_routes, prefix="/api/v1")
app.include_router(chatbot_routes)
app.include_router(file_upload_routes)

# add_routes(
#     app,
#     prompt | llm,
#     path="/chat_with_ollama"
# )

if __name__ == "__main__":
    import uvicorn
    from app.chatbot.vector_store.db import sync_connection
    table_name = "message_history"
    PostgresChatMessageHistory.create_tables(sync_connection, table_name)
    uvicorn.run(app, host="localhost", port=8000)
