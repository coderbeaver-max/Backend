from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from models.request_models import Model
from utils.validators import validate_request
from Services.gemini_service import stream_gemini_response
from Services.database_service import (
    create_conversation,
    save_message,
    get_recent_messages
)

router = APIRouter()


@router.post("/api/stream")
def stream_gemini_response_route(model: Model):
    validate_request(model)

    if model.conversation_id is None:
        conversation_id = create_conversation(
            user_id=model.user_id
        )
    else:
        conversation_id = model.conversation_id

    previous_messages = get_recent_messages(
        conversation_id=conversation_id
    )

    save_message(
        conversation_id=conversation_id,
        role="user",
        content=model.question
    )

    def generate():
        full_response = ""

        for chunk in stream_gemini_response(
            question=model.question,
            model_name=model.model,
            previous_messages=previous_messages
        ):
            full_response += chunk
            yield chunk

        save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache"
        }
    )