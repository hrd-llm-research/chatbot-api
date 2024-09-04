from fastapi import APIRouter, Depends, status, HTTPException
from . import chain, schemas, dependencies
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

router = APIRouter(
    prefix="/npl2sql",
    tags=["npl2sql"]
)
"""postgresql+psycopg2://postgres:123@localhost:5433/btb_homework_db"""
@router.post("/chat")
def npl2sql(request: schemas.NPLRequest):
    result = chain.npl2sql(request)
    return {
        "payload": result
    }
    
    
# @router.post("/database_connection")
def database_connection(database_type: dependencies.Database,request: dependencies.DatabaseConnectionRequest):
    db = dependencies.db_connection(request,database_type )
    return db

@router.post("classify_question")
def classify_question(
    question: str, 
    db: Session = Depends(database_connection)
):
    try:
        result = chain.npl_branching(db, question)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "You are registered successfully.",
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