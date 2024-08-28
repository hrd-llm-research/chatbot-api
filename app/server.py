from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from app.auth.routes import router as auth_routes
from app.chatbot.routes import router as chatbot_routes
from app.chat_with_llm.routes import router as chat_with_llm
from app.chat_with_llm.routes import llm, prompt
app = FastAPI()
app.include_router(auth_routes, prefix="/api/v1")
app.include_router(chatbot_routes)

add_routes(
    app,
    llm,
    path="/chat_with_llm"
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
