from fastapi import APIRouter, Depends, status, HTTPException
from . import chain, schemas, dependencies
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from app.utils import get_db
from app.auth.dependencies import get_current_active_user, transform_user_dto
from app.auth.crud import get_user_by_email
from typing import Annotated
from app.auth.schemas import User
from app.chatbot.dependencies import save_message_to_minio

import os

current_dir = os.path.dirname(os.path.abspath(__file__))

router = APIRouter(
    prefix="/npl2sql",
    tags=["npl2sql"]
)
"""postgresql+psycopg2://postgres:123@localhost:5433/btb_homework_db"""
# @router.post("/chat")
def npl2sql(request: schemas.NPLRequest):
    result = chain.npl2sql(request)
    return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Message was generated successfully.",
                "payload": result,
                "success": True,
            }
    )
    
    
# @router.post("/database_connection")
def database_connection(database_type: dependencies.Database,request: dependencies.DatabaseConnectionRequest):
    db = dependencies.db_connection(request,database_type )
    return db

# @router.post("/classify_question")
def classify_question(
    question: str, 
    db: Session = Depends(database_connection)
):
    try:
        result = chain.npl_branching(db, question)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Message was generated successfully.",
                "payload": result,
                "success": True,
            }
    )
    except Exception:
        result = "Unable to execute"
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=result,
    )
    
@router.post("/npl_with_memory")
def npl_with_memory(
    question, 
    session_id, 
    database_type: dependencies.Database,
    connection_request: dependencies.DatabaseConnectionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)
    result = chain.npl_with_history(question, session_id, database_type.value, connection_request, db, transform_user)
    return result

@router.post("/save_chat_session")
async def save_chat_session(
    session_id: str, 
    current_user: Annotated[User, Depends(get_current_active_user)], 
    db: Session = Depends(get_db),
                    
):
    user = get_user_by_email(db, current_user.email)
    transform_user = transform_user_dto(user)

    save_message_to_minio(db, session_id, transform_user, current_dir)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Chat session have been saved successfully",
            "success": True,
        }
    )
    
@router.post("/generate_sql")
async def sql_generation(
    question, 
    database_type: dependencies.Database,
    connection_request: dependencies.DatabaseConnectionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)], 
):
    response = chain.sql_generation(question, database_type.value, connection_request)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": "Chat session have been saved successfully",
            "success": True,
            "payload":response
        }
    )