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
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Chatbot API",
    description="A simple chatbot API with Langchain and FastAPI",
    version="1.0.0",
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth_routes, prefix="/api/v1")
app.include_router(chatbot_routes, prefix="/api/v1")
app.include_router(file_upload_routes, prefix="/api/v1")
app.include_router(chat_with_sql_routes, prefix="/api/v1")
app.include_router(api_generated_routes, prefix="/api/v1")

from app.chatbot.chain2 import chain

add_routes(
    app,
    chain,
    path="/chat"
)


# @app.middleware("http")
# async def db_session_middleware(request: Request, call_next):
#     response = Response("Internal server error", status_code=500)
#     try:
#         request.state.db = SessionLocal()
#         response = await call_next(request)
#     finally:
#         request.state.db.close()
#     return response





# from app.chatbot.test_chain import chain, rag_chain, Question, llm
# from pydantic import BaseModel
# import asyncio
# from fastapi.responses import StreamingResponse

# """ using langserve endpoint (working)"""
# add_routes(
#     app,
#     chain,
#     path="/chat_serve"
# )

# """" using stream endpoint (working)"""
# async def sync_to_async_gen(sync_gen):
#     for item in sync_gen:
#         yield item  # Yield each item asynchronously
#         await asyncio.sleep(0) 

# # This function will stream the response
# async def stream_qa_response(question: Question):
#     # Assuming you already have the LLM setup with streaming
#     sync_gen = chain.stream({"input": question.input, "collection_name": question.collection_name})

#     # Wrap the synchronous generator and iterate asynchronously
#     async for chunk in sync_to_async_gen(sync_gen):
#         yield f"data: {chunk}\n\n"
#         await asyncio.sleep(0.01) 

# @app.post("/stream")
# async def stream_response(question: Question):
#     return StreamingResponse(stream_qa_response(question), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
