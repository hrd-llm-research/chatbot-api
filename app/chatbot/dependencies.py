import os
import json
from . import crud
from app.message_history import dependencies
from sqlalchemy.orm import Session
from app.auth import schemas
from fastapi import HTTPException, status
from langchain_core.messages import SystemMessage

def write_history_message_as_json(message_list, file:str):
    # Create a list of messages with type and content
    messages_list = [{"type": message.__class__.__name__, "content": message.content} for message in message_list]

    # Determine the directory for storing the file
    current_dir = os.path.dirname(os.path.dirname(__file__))
    history_dir = os.path.join(current_dir,"chatbot", "history")
    json_dir = os.path.join(current_dir,"chatbot", "history", "json", file)

    # Ensure the 'history' directory exists
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)

    file_path = os.path.join(history_dir, json_dir)

    # Check if the file exists and has valid content, otherwise initialize an empty list
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as as_file:
                # Load the existing data
                existing_data = json.load(as_file)
        except json.JSONDecodeError:
            # If the file is empty or corrupted, initialize with an empty list
            existing_data = []
    else:
        # If the file doesn't exist, initialize with an empty list
        existing_data = []

    # Append the new messages to the existing data
    existing_data.extend(messages_list)

    # Write the updated data back to the file
    with open(file_path, "w+") as as_file:
        json.dump(existing_data, as_file, indent=4)
        
def write_history_message(message_list, file: str):
        
    with open(file, 'a+') as as_file:
        for data in message_list:
            as_file.write(f"{data.__class__.__name__}(content='{data.content}'),")
    

def save_message_to_minio(db: Session, session_id, user: schemas.UserResponse, current_dir):
    try:
        history_data = crud.get_history_message_by_session_id(db, session_id)
        local_files = os.listdir(os.path.join(current_dir, "history"))
        
        txt_file = history_data[0]+".txt"
        no_file_to_upload = True
        for local_file in local_files:
            if txt_file == local_file: 
                history_file_dir = os.path.join(current_dir,"history", txt_file)
                dependencies.upload_file(user.username, txt_file, history_file_dir)
                os.remove(history_file_dir)
                

        """" upload json to minio """
        json_file = history_data[0]+".json"
        json_local_files = os.listdir(os.path.join(current_dir, "history", "json"))
        for local_file in json_local_files:
            if json_file == local_file: 
                history_file_dir = os.path.join(current_dir, "history", "json", json_file)
                dependencies.upload_file(user.username, json_file, history_file_dir)
                os.remove(history_file_dir)
                no_file_to_upload = False
                
        if no_file_to_upload:
            print("Up to date.")
    except Exception as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(exception)
        )    
   
def get_histories_by_session_id(session_id, user, db):
    import json 
    
    # store message using txt
    file_name = user.username+"@"+session_id
    json_file = file_name+".json"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    history_dir = os.path.join(current_dir,"history")
    json_dir = os.path.join(history_dir, "json", json_file)
    
    # get history from database
    result_from_db = crud.get_histoy_by_session_id(db, session_id)
    # if exists
    if not result_from_db == None:
        # if there is message history then download minIO server
        if not os.path.exists(json_dir):
            dependencies.download_file_from_MinIO(user.username, json_file, json_dir)
               
    if os.path.exists(json_dir):
        with open(json_dir, "r") as as_json_file:
            data = json.load(as_json_file)
        return data


def write_ai_message(request, user, db):
    ai_message = request.message
    session_id = request.session_id
    
    file_name = user.username+"@"+session_id
    file = file_name+".txt"
    current_dir = os.path.dirname(os.path.abspath(__file__))
    history_dir = os.path.join(current_dir,"history")
    file_dir = os.path.join(history_dir, file)
    json_dir = os.path.join(history_dir, "json", f"{file_name}.json")
    
    chat_history = []
    chat_history.append(SystemMessage(content=ai_message))
    
    write_history_message(chat_history, file_dir)
    write_history_message_as_json(chat_history, json_dir)
    