import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.embeddings import FastEmbedEmbeddings
from app.chatbot.vector_store.db import CONNECTION_STRING
from langchain_community.vectorstores import PGVector
import uuid
from . import crud, schemas
from sqlalchemy.orm import Session
from app.message_history import dependencies
from app.auth.schemas import UserResponse
from langchain_chroma import Chroma
from fastapi import HTTPException,status
from langchain_community.llms import Ollama
from langsmith import traceable

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
    max_tokens=3225
    # top_p=0.9  # Nucleus sampling with top_p of 0.9
)

"""" use local model ollama"""

# llm = Ollama(
#     model = "llama3.1", 
#     temperature=0.7,
    
# )

@traceable()
def retrieval_document_from_chroma(chroma_db_name: str, top_k: int=10, score_threshold: float=0.3):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    persistent_dir = os.path.join(current_dir, "..", "file_upload", "chroma_db", chroma_db_name)
    if not os.path.exists(persistent_dir):
        raise HTTPException(
            status_code=404,
            detail=f"Chroma database '{chroma_db_name}' does not exist in the directory."
        )
    vector_store = Chroma(
        embedding_function=embeddings,
        persist_directory=persistent_dir
    )
    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": top_k, "score_threshold": score_threshold},
    )
    return retriever


def retrieval_collection(collection_name: str, top_k: int=5, score_threshold: float = 0.5):
    vector_store = PGVector(
        collection_name = collection_name,
        connection_string=CONNECTION_STRING,
        embedding_function=embeddings
    )   
    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": top_k, "score_threshold": score_threshold},
    )
    return retriever

def create_chain(retriever):
    # Contextualize question prompt
    # This system prompt helps the AI understand that it should reformulate the question
    # based on the chat history to make it a standalone question
    contextualize_q_system_prompt = (
        """
            You are a helpful assistant designed to assist users by answering questions based on the content of documents they have uploaded. 
            Additionally, you have access to the chat history to provide context for the current conversation. 

            Your task is to formulate a standalone question based on the user's current question and any relevant information from the chat history. 
            Ensure that the reformulated question is clear, concise, and understandable without any need for the previous chat history. 

            If the user's question refers to something mentioned earlier in the conversation, incorporate that information into the new question. 
            Always aim to create a question that fully captures the user's intent in a way that is independent of the conversation's context.

        """
    )

    # Create a prompt template for contextualizing the questions 
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )
    # Create a history-aware retriever
    history_aware_retriever = create_history_aware_retriever(
        llm,
        retriever,
        contextualize_q_prompt
    )

    # Answer and question prompt
    qa_system_prompt = (
        """
            You are a knowledgeable assistant designed to assist users by answering questions based on the content of documents they have retrieved. You can also use the chat history to provide additional context for the current conversation. Your task is to generate a detailed, thoughtful, and well-rounded answer based on the retrieved documents and the user's current question.

            When formulating your response:

            Prioritize using the retrieved documents to provide fact-based, relevant, and accurate answers.
            Elaborate where possible, including examples, further context, and multiple perspectives if applicable.
            If multiple documents are retrieved, synthesize information from them to offer a comprehensive answer, combining key points.
            Vary your responses to similar questions by offering new details, angles, or deeper insights each time the question is asked.
            If no relevant information is found in the retrieved documents, let the user know politely and suggest alternative ways to find the answer (e.g., rephrasing the question).
            Keep your answers clear, concise, and easy to understand, while being mindful of the user's intent.
            If the user's question references something from the chat history, incorporate that information appropriately, but ensure the answer is standalone and understandable without needing to reference previous conversation turns.


            {context}
        """
    )

    # Create a prompt template for answering questions
    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            # MessagesPlaceholder("context"),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )

    # Create a chain to combine documents for question answering
    question_answer_chain = create_stuff_documents_chain(
        llm,
        qa_prompt
    )

    # Create retriver chain that combines the history-aware retriever and the question anwering
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    # chain = rag_chain | StrOutputParser()
    # return chain
    return rag_chain


def chat_with_collection(collection_name: str, question: str, session_id: uuid, db: Session, user: UserResponse):
    try:
        file_name = user.username+session_id
        file = file_name+".txt"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        history_dir = os.path.join(current_dir,"history")
        file_dir = os.path.join(history_dir, file)
        
        result = crud.get_histoy_by_session_id(db, session_id)
        
        # If no history found, get from the chat history of the session_id
        if result == None:
            # Insert to database
            history_data = schemas.HistoryMessageCreate(
                user_id=user.id,
                session_id=session_id,
                history_message_file=file[:-4]
            )
            crud.create_history_message(db, history_data)
        else:
            """
                get from MinIO if history message id exist
            """ 
            if not os.path.exists(file_dir):
                dependencies.download_file_from_MinIO(user.username, file, file_dir)
            
        
        """check if the directory exists"""
        chat_history=[]
        if os.path.exists(file_dir):
            with open(file_dir, "r") as text_file:
                data = text_file.readlines()
            chat_history = data
        
        """"Invoke chatbot"""
        retriever = retrieval_collection(collection_name)
        result = create_chain(retriever).invoke({"input":question, "chat_history":chat_history})

        new_chat_history = []
        new_chat_history.append(HumanMessage(question))
        new_chat_history.append(SystemMessage(result['answer']))

        # write to local file
        from .dependencies import write_history_message
        write_history_message(new_chat_history, file_dir)
        
        return result['answer']
    except Exception as exception:
        return {"error": "An unexpected error occurred.", "detail": str(exception)}
    
@traceable(
    run_type="chain",
    name="Chatbot_with_document"
)
def chat_with_chroma_db(chroma_db_name: str, question: str, session_id: uuid, db: Session, user: UserResponse):
    try:
        # store message using txt
        file_name = user.username+"@"+session_id
        file = file_name+".txt"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        history_dir = os.path.join(current_dir,"history")
        file_dir = os.path.join(history_dir, file)
        
        persistent_dir = os.path.join(current_dir, "..", "file_upload", "chroma_db", chroma_db_name)
        if not os.path.exists(persistent_dir):
            raise HTTPException(
                status_code=404,
                detail=f"Chroma database '{chroma_db_name}' does not exist in the directory."
            )
            
        
        """check if the directory exists"""
        chat_history=[]
        
        # get history from database
        result_from_db = crud.get_histoy_by_session_id(db, session_id)
        # if exists
        if not result_from_db == None:
            # if there is message history then download minIO server
            if not os.path.exists(file_dir):
                dependencies.download_file_from_MinIO(user.username, file, file_dir)
               
            if os.path.exists(file_dir):
                with open(file_dir, "r") as text_file:
                    data = text_file.readlines()
                chat_history = data
        
        """"Invoke chatbot"""
        retriever = retrieval_document_from_chroma(chroma_db_name)
        result = create_chain(retriever).invoke({"input":question, "chat_history":chat_history})
        
        response = parseResponse(result['answer'])
        
        new_chat_history = []
        new_chat_history.append(HumanMessage(content=question))
        new_chat_history.append(SystemMessage(content=result['answer']))

        # If no history found, store message history key into database
        if result_from_db == None:
            # Insert to database
            history_data = schemas.HistoryMessageCreate(
                user_id=user.id,
                session_id=session_id,
                history_message_file=file[:-4]
            )
            crud.create_history_message(db, history_data) 
            
        # write to local file
        from .dependencies import write_history_message
        write_history_message(new_chat_history, file_dir)

        return response
        
    except Exception as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(exception)
        )
    
def parseResponse(response):
    result = response.strip().replace("\n","").replace("SystemMessage(content='", "").replace("')","").replace('\"', '')
    return result