
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
    # Replace the external Gemini call with a predictable test result.
    def fake_gemini_response(question, model_name):
        return "Python is a programming language."

    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        fake_gemini_response,
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
