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

load_dotenv()

embeddings = FastEmbedEmbeddings()

llm = ChatGroq(
    model=os.environ.get('OPENAI_MODEL_NAME')
)

def retriveal_documents(top_k: int=3, score_threshold: float=0.5):
    vector_store = PGVector(
        connection_string=CONNECTION_STRING,
        embedding_function=embeddings
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

    # Create a chain to combine documents for question answering
    question_answer_chain = create_stuff_documents_chain(
        llm,
        qa_prompt
    )

    # Create retriver chain that combines the history-aware retriever and the question anwering
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    return rag_chain


def chat_with_collection(collection_name: str, question: str, session_id: uuid, db: Session, user: UserResponse):
    try:
        username = "sokheang"
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
                history_id=file
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