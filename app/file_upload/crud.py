from sqlalchemy.orm import Session
from sqlalchemy import text
from app.auth.models import ChromaDB
from app.auth.schemas import ChromaSchemaDB

def alter_table_langchain_collection(db: Session):
    try:
        column_check = db.execute(
            text("""
                SELECT attname
                FROM pg_catalog.pg_attribute
                WHERE attrelid = 'langchain_pg_collection'::regclass
                AND attname = 'user_id'
                AND NOT attisdropped;     
            """)
        ).fetchone()    

        if column_check is None:
            # If column does not exist, add it
            db.execute(text("""
                ALTER TABLE langchain_pg_collection 
                ADD COLUMN user_id INTEGER,
                ADD CONSTRAINT fk_user
                FOREIGN KEY (user_id) REFERENCES users(id)                  
            """))  
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
 
def add_user_id_to_langchain_db_collection(db: Session, user_id: int, collection_name: str):
    try:
        db.execute(
                text(f"""
                    UPDATE langchain_pg_collection SET user_id = {user_id} WHERE name = '{collection_name}';     
                """)
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    
def create_chroma(db: Session, id: int, filename: str):
    db_chroma_data = ChromaDB(
        user_id = id,
        chroma_name = filename
    )
    db.add(db_chroma_data)
    db.commit()
    db.refresh(db_chroma_data)
    return db_chroma_data

def get_all_chroma_db(db: Session, user_id:int):
    return db.query(ChromaDB).filter(ChromaDB.user_id == user_id).all()

def delete_chroma_db_by_chroma_db_name(db: Session, chroma_db_name:str, user_id:int):
    db.query(ChromaDB).filter(ChromaDB.chroma_name == chroma_db_name and ChromaDB.user_id == user_id).delete()
    
def get_chroma_db_by_chroma_db_name(db: Session, chroma_db_name:str, user_id:int):
    return db.query(ChromaDB).filter(ChromaDB.chroma_name == chroma_db_name and ChromaDB.user_id == user_id).first()