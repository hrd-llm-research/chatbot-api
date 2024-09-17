import os
import uuid

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
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
from fastapi import HTTPException,status
from langchain_community.llms import Ollama
from langsmith import traceable

load_dotenv()

llm = ChatGroq(
    model=os.environ.get('OPENAI_MODEL_NAME')
)

"""" use local model ollama"""

# llm = Ollama(
#     model = "llama3.1", 
#     temperature=0.7,
# )    

PROMPT_SUFFIX = """Only use the following tables:
{table_info}

Question: {input}"""

_postgres_template = """"
    You are a PostgreSQL expert. Given an input question, first create a syntactically correct PostgreSQL query to run, then look at the results of the query and return the answer to the input question.
    
    Do not include sensitive columns such as "password", "api_key", or other confidential fields in your query. 
    When asked to generate a query, never use "SELECT *". Instead, select only the columns necessary to answer the question. \
    You must explicitly specify each column you are selecting. If the user does not mention specific columns, select only the most relevant columns.
    
    Unless the user specifies in the question a specific number of examples to obtain, query for at most {top_k} results using the LIMIT clause as per PostgreSQL. You can order the results to return the most informative data in the database.\
                
    Never query for all columns from a table. You must query only the columns that are needed to answer the question. \
                
    Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table. 
    Pay attention to use CURRENT_DATE function to get the current date, if the question involves "today".

    Use the following format:

    Question: Question here
    SQLQuery: SQL Query to run
    SQLResult: Result of the SQLQuery
    Answer: Final answer here
"""

_mysql_template = """"
    You are a MySQL expert. Given an input question, first create a syntactically correct MySQL query to run, then look at the results of the query and return the answer to the input question.
    
    Do not include sensitive columns such as "password", "api_key", or other confidential fields in your query. 
    When asked to generate a query, never use "SELECT *". Instead, select only the columns necessary to answer the question. \
    You must explicitly specify each column you are selecting. If the user does not mention specific columns, select only the most relevant columns.
    
    Unless the user specifies in the question a specific number of examples to obtain, query for at most {top_k} results using the LIMIT clause as per MySQL. You can order the results to return the most informative data in the database. \
    
    Never query for all columns from a table. You must query only the columns that are needed to answer the question. You must query only the columns that are needed to answer the question. \
    
    Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table. Pay attention to not query password columns which in the table.
    Pay attention to use CURDATE() function to get the current date, if the question involves "today".

    Use the following format:

    Question: Question here
    SQLQuery: SQL Query to run
    SQLResult: Result of the SQLQuery
    Answer: Final answer here
"""

POSTGRES_PROMPT = PromptTemplate(
    input_variables=["input", "table_info", "top_k"],
    template=_postgres_template + PROMPT_SUFFIX
)
        
MYSQL_PROMPT = PromptTemplate(
    input_variables=["input", "table_info", "top_k"],
    template=_mysql_template + PROMPT_SUFFIX
)

def parseResponseToSQL(response):

    if "SQLQuery:" in response:
        sql_query = response.split("SQLQuery:")[1].strip()
        
    else:
        raise ValueError("SQL query not found in the result")
    return sql_query.strip().replace('\"','').replace('\n', ' ').replace('`', '').replace('sql', '').replace('\t','').replace('\\','')


def parseResponseToSQLStatementCode(response):

    if "SQLQuery:" in response:
        sql_query = response.split("SQLQuery:")[1].strip()
        
    else:
        raise ValueError("SQL query not found in the result")
    parse_data = sql_query.strip().replace('\"','').replace('\n', ' ').replace('sql', '').replace('\t','').replace('\\','')
    return "```"+parse_data+"```"

def npl2sql(request: schemas.NPLRequest):
    db = SQLDatabase.from_uri(request.connection_db)

    executed_query = QuerySQLDataBaseTool(db=db)
    write_query = create_sql_query_chain(llm=llm, db=db)
    
    chain = write_query | parseResponseToSQL | executed_query
    
    result = chain.invoke({"question":request.question})

    return result


def npl_branching(db: Session, question: str):
    
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

@traceable(
    run_type="chain",
    name="Classfy question"
)
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

@traceable(
    run_type="chain",
    name="Chat_with_SQL"
)    
def npl_with_history(question: str, session_id: uuid, database_type, database_connection, db1, user):
    try:
        
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
        write_query = create_sql_query_chain(
            llm=llm, 
            db=db,
            prompt = POSTGRES_PROMPT if database_type == "postgresql" else MYSQL_PROMPT,
        )
        
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
                lambda output: (write_query | parseResponseToSQL | executed_query).invoke({
                    "question":output['question']
                }) 
                
                # lambda output: {
                #     "sql_query": (write_query| parseResponseToSQL).invoke({"question":output['question']}),
                #     "result": execute_and_format_query(db, write_query.invoke({"question": output['question']}))
                # }
            ),
            (
                lambda output: "sensitive" in output['classification'].lower(),  # Check if output contains "sensitive"
                lambda output: {"response": "sensitive data can't generate"}  # Provide a response if sensitive
            ),
            lambda output: {"response": f"unable to classify the question."}  # Default response if none match
        )
        
        """" Get history messages"""
        result_from_db = get_histoy_by_session_id(db1, session_id)
                    
        # read history from file
        chat_history=[]
        
        # if exists
        if not result_from_db == None:
            """
                if there is message history then download minIO server
            """ 
            if not os.path.exists(file_dir):
                download_file_from_MinIO(user.username, file_name, file_dir)
               
            if os.path.exists(file_dir):
                with open(file_dir, "r") as text_file:
                    data = text_file.readlines()
                chat_history = data

        # invoke history aware function
        res = classify_chain.invoke({"input": question, "chat_history":chat_history})
        if isinstance(res, str):
            res = {"classification": res.strip(), "question": question}

        result = branches.invoke(res)
        # sql_query = result.get("sql_query")
        # query_result = result.get("result")
        
        # print("result: ", result)
        
        # final_result = {
        #     "sql_query": sql_query,
        #     "result": query_result
        # }
        
        # write history
        # new_chat_history = []
        # new_chat_history.append(HumanMessage(content=question))
        # new_chat_history.append(SystemMessage(content=result["result"]))
            
        """
            If no history found, store message history key into database
        """
        # if result == None:
        #         # Insert to database
        #         history_data = HistoryMessageCreate(
        #             user_id=user.id,
        #             session_id=session_id,
        #             history_message_file=file_name[:-4]
        #         )
        #         create_history_message(db1, history_data)


        """
            write to local file
        """
        # from app.chatbot.dependencies import write_history_message
        # write_history_message(new_chat_history, file_dir)

        return result
    
    except Exception as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(exception) 
        )    
    
    
def sql_generation(question: str, database_type, database_connection):
    
    try:
                

        if database_type == "postgresql":
            db = SQLDatabase.from_uri(f"postgresql+psycopg2://{database_connection.username}:{database_connection.password}@{database_connection.host}:{database_connection.port}/{database_connection.database}")
        elif database_type == "mysql":
            db = SQLDatabase.from_uri(f"mysql+pymysql://{database_connection.username}:{database_connection.password}@{database_connection.host}:{database_connection.port}/{database_connection.database}")
            
        write_query = create_sql_query_chain(
            llm = llm, 
            db = db,
            prompt = POSTGRES_PROMPT if database_type == "postgresql" else MYSQL_PROMPT,
        )
        result = write_query.invoke({"question":question})
        
        return parseResponseToSQL(result)
    
    except Exception as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(exception)
        )    
        
def execute_and_format_query(db, sql_query: str):
    print("DB: ",db)
    """
    Executes the SQL query and formats the result to include column names.
    """
    # Use your database connection to execute the query
    cursor = db.connection().execute(sql_query)
    
    # Get column names from the cursor
    column_names = [desc[0] for desc in cursor.description]

    # Fetch the query result
    rows = cursor.fetchall()

    # Format the result as a list of dictionaries, where keys are column names
    result_with_columns = [dict(zip(column_names, row)) for row in rows]

    return result_with_columns
