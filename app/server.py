import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from langserve import add_routes
from app.auth.routes import router as auth_routes
from app.chatbot.routes import router as chatbot_routes
from app.file_upload.routes import router as file_upload_routes
from app.auth.database import SessionLocal
from app.chat_with_sql.routes import router as chat_with_sql_routes
from app.api_generated.routes import router as api_generated_routes

app = FastAPI(
    title="Chatbot API",
    description="A simple chatbot API with Langchain and FastAPI",
    version="1.0.0",
)
app.include_router(auth_routes, prefix="/api/v1")
app.include_router(chatbot_routes, prefix="/api/v1")
app.include_router(file_upload_routes, prefix="/api/v1")
app.include_router(chat_with_sql_routes, prefix="/api/v1")
app.include_router(api_generated_routes, prefix="/api/v1")

# @app.middleware("http")
# async def db_session_middleware(request: Request, call_next):
#     response = Response("Internal server error", status_code=500)
#     try:
#         request.state.db = SessionLocal()
#         response = await call_next(request)
#     finally:
#         request.state.db.close()
#     return response


# from app.chatbot.test_chain import chain

# add_routes(
#     app,
#     chain,
#     path="/chat_serve"
# )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
