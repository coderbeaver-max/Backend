from fastapi import HTTPException
from config.settings import ALLOWED_MODELS

def validate_request(model):
    if not model.question.strip():
        raise HTTPException(
            status_code=400,
            detail="question can't be empty"
        )
    
    if not model.user_id.strip():
        raise HTTPException(
            status_code=400,
            detail="user id can't be empty"
        )
    
    if len(model.question)>500:
        raise HTTPException(
            status_code=400,
            detail="question length can't be greater than 500"
        )
    
    if model.model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400,
            detail="not a valid gemini model"
        )