import os
import json
from . import crud
from app.message_history import dependencies
from sqlalchemy.orm import Session
from app.auth import schemas
from fastapi import HTTPException, status

# current_dir = os.path.dirname(os.path.abspath(__file__))
def write_history_message(list, file: str):
        
    with open(file, 'a+') as as_file:
        for data in list:
            as_file.write(f"{data.__class__.__name__}(content='{data.content}'),")
    
            
    # messages_list = [{"type": message.__class__.__name__, "content": message.content} for message in list]

    # # Write the JSON to a file
    # with open(os.path.join(current_dir,"history", "sample.json"), "w") as file:
    #     json.dump(messages_list, file, indent=4)


def save_message_to_minio(db: Session, session_id, user: schemas.UserResponse, current_dir):
    try:
        history_data = crud.get_history_message_by_session_id(db, session_id)
        local_files = os.listdir(os.path.join(current_dir, "history"))
        
        no_file_to_upload = True
        for local_file in local_files:
            if history_data[0] == local_file: 
                history_file_dir = os.path.join(current_dir,"history", history_data[0])
                dependencies.upload_file(user.username, history_data[0], history_file_dir)
                os.remove(history_file_dir)
                no_file_to_upload = False
                
        if no_file_to_upload:
            print("Up to date.")
    except Exception as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(exception)
        )    
    