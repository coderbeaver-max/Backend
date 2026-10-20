
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("GEMINI_API_KEY", "ci-test-key")

from fastapi.testclient import TestClient

from GenAPI import app
import routes.ask as ask_route


client = TestClient(app)


def test_ask_returns_generated_response(monkeypatch):
    """The API returns the generated answer without real external services."""

    def fake_gemini_response(question, model_name):
        return "Python is a programming language."

    def fake_create_conversation(user_id):
        return "ci-test-conversation"

    def fake_save_message(*args, **kwargs):
        return None

    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        fake_gemini_response,
    )
    monkeypatch.setattr(
        ask_route,
        "create_conversation",
        fake_create_conversation,
    )
    monkeypatch.setattr(
        ask_route,
        "save_message",
        fake_save_message,
    )

    payload = {
        "user_id": "ci-test-user",
        "question": "What is Python?",
        "model": "gemini-2.5-flash",
    }

    response = client.post("/api/ask", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "What is Python?"
    assert data["user_id"] == "ci-test-user"
    assert data["model_name"] == "gemini-2.5-flash"
    assert data["response"] == "Python is a programming language."


def test_ask_rejects_missing_question():
    """The API rejects a request without the required question field."""

    payload = {
        "user_id": "ci-test-user",
        "model": "gemini-2.5-flash",
    }

    response = client.post("/api/ask", json=payload)

    assert response.status_code == 422


def test_ask_rejects_missing_user_id():
    """The API rejects a request without the required user_id field."""

    payload = {
        "question": "What is Python?",
        "model": "gemini-2.5-flash",
    }

    response = client.post("/api/ask", json=payload)

    assert response.status_code == 422



def test_ask_uses_default_model_when_model_is_missing(monkeypatch):
    """The API uses gemini-2.5-flash when model is omitted."""

    def fake_gemini_response(question, model_name):
        assert model_name == "gemini-2.5-flash"
        return "Python is a programming language."

    def fake_create_conversation(user_id):
        return "ci-test-conversation"

    def fake_save_message(*args, **kwargs):
        return None

    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        fake_gemini_response,
    )
    monkeypatch.setattr(
        ask_route,
        "create_conversation",
        fake_create_conversation,
    )
    monkeypatch.setattr(
        ask_route,
        "save_message",
        fake_save_message,
    )

    payload = {
        "user_id": "ci-test-user",
        "question": "What is Python?",
    }

    response = client.post("/api/ask", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["model_name"] == "gemini-2.5-flash"
    assert data["response"] == "Python is a programming language."

def test_ask_rejects_unsupported_model(monkeypatch):
    """An unsupported model should not generate an AI response."""

    def fail_if_gemini_called(*args, **kwargs):
        raise AssertionError(
            "Gemini should not be called for an unsupported model."
        )

    def fake_create_conversation(user_id):
        return "ci-test-conversation"

    def fake_save_message(*args, **kwargs):
        return None

    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        fail_if_gemini_called,
    )
    monkeypatch.setattr(
        ask_route,
        "create_conversation",
        fake_create_conversation,
    )
    monkeypatch.setattr(
        ask_route,
        "save_message",
        fake_save_message,
    )

    payload = {
        "user_id": "ci-test-user",
        "question": "What is Python?",
        "model": "unsupported-model",
    }

    response = client.post("/api/ask", json=payload)

    assert response.status_code in (400, 422)

def test_ask_handles_conversation_database_failure(monkeypatch):
    """A conversation creation failure should return HTTP 500."""

    def fail_create_conversation(user_id):
        raise RuntimeError("Simulated database connection failure")

    def fail_if_gemini_called(*args, **kwargs):
        raise AssertionError(
            "Gemini should not run if conversation creation fails."
        )

    monkeypatch.setattr(
        ask_route,
        "create_conversation",
        fail_create_conversation,
    )
    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        fail_if_gemini_called,
    )

    test_client = TestClient(app, raise_server_exceptions=False)

    response = test_client.post(
        "/api/ask",
        json={
            "user_id": "ci-test-user",
            "question": "What is Python?",
            "model": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 500


def test_ask_handles_gemini_failure(monkeypatch):
    """A Gemini generation failure should return HTTP 500."""

    def fake_create_conversation(user_id):
        return "ci-test-conversation"

    def fail_gemini(question, model_name):
        raise RuntimeError("Simulated Gemini service failure")

    def fake_save_message(*args, **kwargs):
        return None

    monkeypatch.setattr(
        ask_route,
        "create_conversation",
        fake_create_conversation,
    )
    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        fail_gemini,
    )
    monkeypatch.setattr(
        ask_route,
        "save_message",
        fake_save_message,
    )

    test_client = TestClient(app, raise_server_exceptions=False)

    response = test_client.post(
        "/api/ask",
        json={
            "user_id": "ci-test-user",
            "question": "What is Python?",
            "model": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 500


def test_ask_handles_message_persistence_failure(monkeypatch):
    """A message-saving failure should return HTTP 500."""

    def fake_create_conversation(user_id):
        return "ci-test-conversation"

    def fake_gemini(question, model_name):
        return "Python is a programming language."

    def fail_save_message(*args, **kwargs):
        raise RuntimeError("Simulated message persistence failure")

    monkeypatch.setattr(
        ask_route,
        "create_conversation",
        fake_create_conversation,
    )
    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        fake_gemini,
    )
    monkeypatch.setattr(
        ask_route,
        "save_message",
        fail_save_message,
    )

    test_client = TestClient(app, raise_server_exceptions=False)

    response = test_client.post(
        "/api/ask",
        json={
            "user_id": "ci-test-user",
            "question": "What is Python?",
            "model": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 500
