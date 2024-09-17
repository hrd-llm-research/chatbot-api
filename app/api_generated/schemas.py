from enum import Enum
from pydantic import BaseModel

class Provider(Enum):
    GROQ = "groq"
    OPENAI = "openai"
    OLLAMA = "ollama"
    
class Model(Enum):
    GPT35TURBO = "gpt-3.5-turbo"
    LLAMA38B8192 = "Llama3-8b-8192"
    LLAMA3 = "Llama3"