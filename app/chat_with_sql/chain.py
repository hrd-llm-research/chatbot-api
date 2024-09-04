import os

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
    
    classification_chain = classification_template | llm | StrOutputParser()
    res = classification_chain.invoke({"question":question})
    
    if isinstance(res, str):
        res = {"classification": res.strip(), "question": question}
    
    result = branches.invoke(res)

    return result
