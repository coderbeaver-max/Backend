from fastapi import APIRouter

from models.request_models import Model
from utils.validators import validate_request
from Services.gemini_service import generate_gemini_response
from Services.database_service import (
    create_conversation,
    save_message
)

router = APIRouter()


@router.post("/api/ask")
def ask_question(model: Model):

    validate_request(model)

    conversation_id = create_conversation(
        user_id=model.user_id
    )

    save_message(
        conversation_id=conversation_id,
        role="user",
        content=model.question
    )

    response = generate_gemini_response(
        question=model.question,
        model_name=model.model
    )

    save_message(
        conversation_id=conversation_id,
        role="assistant",
        content=response
    )

    return {
        "status": "success",
        "question": model.question,
        "user_id": model.user_id,
        "model_name": model.model,
        "conversation_id": conversation_id,
        "response": response
    }