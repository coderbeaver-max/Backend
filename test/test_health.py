
import os

os.environ.setdefault("GEMINI_API_KEY", "ci-test-key")

from fastapi.testclient import TestClient

from GenAPI import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "Backend running 🚀"
    }


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["gemini"] == "connected"
    assert data["server"] == "running"
    assert isinstance(data["allowed_models"], list)
