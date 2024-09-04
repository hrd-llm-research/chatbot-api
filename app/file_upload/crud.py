from sqlalchemy.orm import Session
from sqlalchemy import text

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