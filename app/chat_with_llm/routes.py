from langchain_community.llms.ollama import Ollama
from langserve import add_routes
from fastapi import APIRouter
from langchain.prompts import ChatPromptTemplate

router = APIRouter()

llm = Ollama(
    model="llama3",
    
)

prompt = ChatPromptTemplate.from_template(
    "Give the best answer {input}"
)

