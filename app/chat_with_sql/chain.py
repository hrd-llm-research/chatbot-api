import os
import uuid

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from . import schemas
from langchain_core.output_parsers import StrOutputParser
from langchain.chains.sql_database.query import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool, QuerySQLCheckerTool
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnableBranch
from sqlalchemy.orm import Session
from app.chatbot.crud import create_history_message, get_histoy_by_session_id
from app.message_history.dependencies import download_file_from_MinIO
from app.chatbot.schemas import HistoryMessageCreate

load_dotenv()

llm = ChatGroq(
    model=os.environ.get('OPENAI_MODEL_NAME')
)

    

my_prompt_template = """You are a SQL expert of {dialect}. 
   Please write an SQL query base on this question: "{question}" and pay attention to use only the column names you can see in the tables below.
   Be careful to not query for columns that do not exist. 
   Also, pay attention to which column is in which table and if you use the SELECT with GROUP BY, please check it, because if it not appear in GROUP BY it will got error.

   Here is database information: {schema_info}

   Only provide the SQL script without any explanation and follow this format for the output: 
   SQL Script: <<Output here>>
   """

def parseResponseToSQL(response):
    # return response.strip().replace("```", "").replace("SQL Script:","")

    if "SQLQuery:" in response:
        sql_query = response.split("SQLQuery:")[1].strip()
        
    else:
        raise ValueError("SQL query not found in the result")
    return sql_query.strip().replace('\"','')

def npl2sql(request: schemas.NPLRequest):
    db = SQLDatabase.from_uri(request.connection_db)

    executed_query = QuerySQLDataBaseTool(db=db)
    write_query = create_sql_query_chain(llm=llm, db=db)
    
    chain = write_query | parseResponseToSQL | executed_query
    
    result = chain.invoke({"question":request.question})

    return result


def npl_branching(db: Session, question: str):
    
   
    # db = SQLDatabase.from_uri("postgresql+psycopg2://postgres:123@localhost:5433/btb_homework_db")
    
    db = SQLDatabase.from_uri(db)
    
    executed_query = QuerySQLDataBaseTool(db=db)
    write_query = create_sql_query_chain(llm=llm, db=db)
    
    
# Define branches for RunnableBranch
    branches = RunnableBranch(
        (
            lambda output: "insensitive" in output['classification'].lower(),  # Check if output contains "insensitive"
            lambda output: (write_query | parseResponseToSQL | executed_query).invoke({"question":output['question']}) 
        ),
        (
            lambda output: "sensitive" in output['classification'].lower(),  # Check if output contains "sensitive"
            lambda output: {"response": "sensitive data can't generate"}  # Provide a response if sensitive
        ),
        lambda output: {"response": f"unable to classify the question."}  # Default response if none match
    )

    res = classify_question(question)
    
    if isinstance(res, str):
        res = {"classification": res.strip(), "question": question}
    
    result = branches.invoke(res)

    return result

def classify_question(question):
    classification_template = ChatPromptTemplate.from_messages(
        [
            ("system", """
                You are a smart and security-conscious assistant. Your task is to determine whether a question related to executing an SQL statement is "sensitive" or "insensitive." 

                A "sensitive" question involves operations that could potentially expose, alter, or delete sensitive data, cause data breaches, escalate privileges, or perform unauthorized access. Examples include, but are not limited to, questions that attempt to access private user information, manipulate critical system settings, or delete important records.

                An "insensitive" question involves harmless operations that do not compromise data integrity, security, or confidentiality. Examples include, but are not limited to, questions that request public information, perform basic data retrieval, or operate on non-sensitive datasets.

                Please classify the following question accordingly:

                Question: "{question}"

                Classification Only (Sensitive or Insensitive) as a keyword:  
                
            """),
            ("human", "{question}")
        ]
    )
    classification_chain = classification_template | llm | StrOutputParser()
    res = classification_chain.invoke({"question":question})
    return res
 



from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables import RunnableBranch
from langchain_core.messages import HumanMessage, SystemMessage

    
def npl_with_history(question: str, session_id: uuid, database_type, database_connection, db1, user):
    file_name = user.username+"@"+session_id+".txt"
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    history_dir = os.path.join(current_dir,"history")
    file_dir = os.path.join(history_dir, file_name)
    
    # db = SQLDatabase.from_uri(db)
    if database_type == "postgresql":
        db = SQLDatabase.from_uri(f"postgresql+psycopg2://{database_connection.username}:{database_connection.password}@{database_connection.host}:{database_connection.port}/{database_connection.database}")
    elif database_type == "mysql":
        db = SQLDatabase.from_uri(f"mysql+pymysql://{database_connection.username}:{database_connection.password}@{database_connection.host}:{database_connection.port}/{database_connection.database}")
    
    executed_query = QuerySQLDataBaseTool(db=db)
    write_query = create_sql_query_chain(llm=llm, db=db)
    
    contextualize_q_system_prompt = (
        """
            Given a chat history and the latest user question 
            which might reference context in the chat history, formulate a standalone question 
            which can be understood without the chat history. Do NOT answer the question, 
            just reformulate it if needed and otherwise return it as is.

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

    # Define a function to run the LLM pipeline with or without history
    def process_with_history(input_dict):
        llm_input = {
            "input": input_dict["input"],
            "chat_history": input_dict["chat_history"]
        }

        return (contextualize_q_prompt | llm | StrOutputParser()).invoke(llm_input)

    # Create a RunnableBranch for handling the question with or without history
    classify_chain = RunnableBranch(
        (
            lambda x: not x.get("chat_history", False),  
            # if no chat history
            lambda x: classify_question(x["input"])  
        ),
        # if have chat history
        lambda x: classify_question(process_with_history(x))
    )
    
    
    # Define branches for RunnableBranch
    branches = RunnableBranch(
        (
            lambda output: "insensitive" in output['classification'].lower(),  # Check if output contains "insensitive"
            lambda output: (write_query | parseResponseToSQL | executed_query).invoke({"question":output['question']}) 
        ),
        (
            lambda output: "sensitive" in output['classification'].lower(),  # Check if output contains "sensitive"
            lambda output: {"response": "sensitive data can't generate"}  # Provide a response if sensitive
        ),
        lambda output: {"response": f"unable to classify the question."}  # Default response if none match
    )
    
    """" Get history messages"""
    result = get_histoy_by_session_id(db1, session_id)
    print("result: ",  result)
    
    if result == None:
            # Insert to database
            history_data = HistoryMessageCreate(
                user_id=user.id,
                session_id=session_id,
                history_message_file=file_name
            )
            create_history_message(db1, history_data)
    else:
        """
            get from MinIO if history message id exist
        """ 
        if not os.path.exists(file_dir):
            download_file_from_MinIO(user.username, file_name, file_dir)
                
    # read history from file
    chat_history=[]
    if os.path.exists(file_dir):
        with open(file_dir, "r") as text_file:
            data = text_file.readlines()
            chat_history = data

    # invoke history aware function
    res = classify_chain.invoke({"input": question, "chat_history":chat_history})
    if isinstance(res, str):
        res = {"classification": res.strip(), "question": question}

    result = branches.invoke(res)
    
    # write history
    new_chat_history = []
    new_chat_history.append(HumanMessage(content=question))
    new_chat_history.append(SystemMessage(content=result))
        
    # write to local file
    from app.chatbot.dependencies import write_history_message
    write_history_message(new_chat_history, file_dir)
    
    return result
    