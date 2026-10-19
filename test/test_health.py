
import os
import sys
from pathlib import Path

# Make the backend repository root importable in local and CI environments.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Health tests must not require a real Gemini API key.
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
