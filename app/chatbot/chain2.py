import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.embeddings import FastEmbedEmbeddings
from . import crud, schemas, dependencies
from app.message_history import dependencies
from langchain_chroma import Chroma
from fastapi import HTTPException
from langsmith import traceable
from langchain.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import Runnable , RunnableSequence
from langchain.schema.output_parser import StrOutputParser
from typing import List, Tuple
from app.utils import get_db
from langchain_huggingface import HuggingFaceEmbeddings


load_dotenv()

# Create embeddings without GPU
embeddings = FastEmbedEmbeddings()

# Create embeddings with GPU
# embedding = HuggingFaceEmbeddings(
#     model_name="BAAI/bge-small-en-v1.5",
#     model_kwargs={'device': 'cuda'},  # Use GPU if available
#     encode_kwargs={'normalize_embeddings': True}
# )

llm = ChatGroq(
    model=os.environ.get('OPENAI_MODEL_NAME'),
    # model="Mixtral-8x7b-32768",
    temperature=1,
    max_tokens=3225,
    # top_p=0.9  # Nucleus sampling with top_p of 0.9
)

"""" use local model ollama"""

# llm = Ollama(
#     model = "llama3.1", 
#     temperature=0.7,
    
# )

    # Answer and question prompt
qa_system_prompt = (
        """
            You are a knowledgeable assistant designed to help users find information from documents they have uploaded. 
            You have access to the content of the document and can provide precise answers based on the text within the document. 
            Always base your responses solely on the information available in the document. 
            If the answer to a user's question is not found in the document, respond by letting them know that the information is not available. 
            Keep your answers clear, concise, and relevant to the user's query.

            {context}
        """
    )

    # Create a prompt template for answering questions
qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )

class RetrievalRunnable(Runnable):

    def invoke(self, inputs: dict, *args, **kwargs) -> dict:
        
        
        from app.auth.database import SessionLocal
        db = SessionLocal()
        
        chat_history = inputs.get("chat_history")
        username = inputs.get("username")
        session_id = inputs.get("session_id")
        question = inputs.get("input")
        chroma_db_name = inputs.get("collection_name")
        
        user_id = crud.get_userId_by_username(db, username)
        
        # store message using txt
        file_name = username+"@"+session_id
        file = file_name+".txt"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        history_dir = os.path.join(current_dir,"history")
        file_dir = os.path.join(history_dir, file)
        json_file = file_name+".json"
        json_dir = os.path.join(current_dir, "history", "json", json_file)
        
        
        persistent_dir = os.path.join(current_dir, "..", "file_upload", "chroma_db", chroma_db_name)
        if not os.path.exists(persistent_dir):
            raise HTTPException(
                status_code=404,
                detail=f"Chroma database '{chroma_db_name}' does not exist in the directory."
            )
            
        result_from_db = crud.get_histoy_by_session_id(db, session_id)
        
        # if exists
        if not result_from_db == None:
            # if there is message history then download minIO server
            if not os.path.exists(file_dir):
                dependencies.download_file_from_MinIO(username, file, file_dir)
                with open(file_dir, "r") as text_file:
                    data = text_file.readlines()
                chat_history = data
                
            if not os.path.exists(json_dir):
                dependencies.download_file_from_MinIO(username, json_file, json_dir)    

        new_chat_history = []
        new_chat_history.append(HumanMessage(content=question))
        
        """write to local file"""
        
        from .dependencies import write_history_message, write_history_message_as_json
        write_history_message(new_chat_history, file_dir)
        write_history_message_as_json(new_chat_history, json_dir)
        
        # If no history found, store message history key into database
        if result_from_db == None:
            # Insert to database
            history_data = schemas.HistoryMessageCreate(
                user_id=user_id[0],
                session_id=session_id,
                history_message_file=file[:-4]
            )
            crud.create_history_message(db, history_data) 
            
        db.close()
        
        vector_store = Chroma(
            embedding_function=embeddings,
            persist_directory=persistent_dir
        )
        retriever = vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 5, "score_threshold": 0.5},
        )
        documents = retriever.invoke(inputs['input'])
        context = " ".join([doc.page_content for doc in documents])
        
        if not context.strip():
            return {
                "context": None,  # Empty context to indicate no document content
                "chroma": chroma_db_name,
                "input": inputs.get("input"),
                "chat_history": chat_history
            }
            
        return {
            "context": context, 
            "chroma": chroma_db_name, 
            "input": inputs.get("input"), 
            "chat_history": chat_history
        }
    

# chain = RunnableSequence(  
#     RetrievalRunnable()
#     | (lambda x: {
#         "context": x["context"], 
#         "input": x["input"],
#         "chat_history": x["chat_history"],
#     })
#     | qa_prompt
#     | llm
#     | StrOutputParser()
# )

chain = RunnableSequence(
    RetrievalRunnable()
    | (lambda x: {
        "context": x["context"] if x["context"] else None,  # Pass context if available
        "input": x["input"],
        "chat_history": x["chat_history"]
    })
    | (lambda x: {"context": x["context"], "input": x["input"], "chat_history": x["chat_history"]} 
        if x["context"] else {"context": None, "input": x["input"], "chat_history": x["chat_history"]})
    | (lambda x: None if x is None else qa_prompt)  # Skip prompt if no context
    | (lambda x: None if x is None else llm)  # Skip LLM if no context
    | StrOutputParser()
)




""" for langserve endpoint"""
from langchain.pydantic_v1 import BaseModel, Field

class Question(BaseModel):
    input: str
    username: str = Field(
        ...,
        extra={"widget": {"type": "chat", "input": "question"}},
    )
    collection_name: str = Field(
        ...,
        extra={"widget": {"type": "chat", "input": "question"}},
    )
    chat_history: List[Tuple[str, str]] = Field(
        ...,
        extra={"widget": {"type": "chat", "input": "question"}},
    )
    session_id: str = Field(
        ...,
        extra={"widget": {"type": "chat", "input": "question"}},
    )

chain = chain.with_types(input_type=Question)