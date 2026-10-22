
from fastapi import APIRouter

from models.request_models import Model
from utils.validators import validate_request
from Services.gemini_service import generate_gemini_response
from Services.database_service import (
    create_conversation,
    save_message,
    create_request_execution,
    finish_request_execution,
)

router = APIRouter()


@router.post("/api/ask")
def ask_question(model: Model):
    validate_request(model)

    # 1. Create a conversation for this request.
    conversation_id = create_conversation(
        user_id=model.user_id
    )

    # 2. Save the user's question.
    save_message(
        conversation_id=conversation_id,
        role="user",
        content=model.question,
    )

    # 3. Record the request as pending before calling Gemini.
    execution_id = create_request_execution(
        conversation_id=conversation_id
    )

    try:
        # 4. Generate the AI response.
        response = generate_gemini_response(
            question=model.question,
            model_name=model.model,
        )

        # 5. Persist the AI response before recording success.
        save_message(
            conversation_id=conversation_id,
            role="assistant",
            content=response,
        )

    except Exception as exc:
        # Record a safe error summary without exposing raw exception details.
        safe_error_message = (
            f"Request processing failed ({type(exc).__name__})."
        )

        try:
            finish_request_execution(
                execution_id=execution_id,
                status="failed",
                error_message=safe_error_message,
            )
        except Exception:
            # Preserve the original processing exception.
            # The execution may remain pending if this update fails.
            pass

        raise

    # 6. Mark the execution successful after the answer is saved.
    finish_request_execution(
        execution_id=execution_id,
        status="succeeded",
    )

    # Preserve the existing API response fields.
    return {
        "status": "success",
        "question": model.question,
        "user_id": model.user_id,
        "model_name": model.model,
        "conversation_id": conversation_id,
        "response": response,
    }
