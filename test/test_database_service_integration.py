
"""Integration tests for the JARVIS PostgreSQL persistence layer.

These tests are restricted to the dedicated GitHub Actions jarvis_test
database. Never weaken the safety guard to run them against production.
"""

import os
import uuid
from urllib.parse import unquote, urlparse

import psycopg2
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GEMINI_API_KEY", "ci-test-key")

from GenAPI import app
import routes.ask as ask_route
from Services.database_service import (
    create_conversation,
    create_request_execution,
    finish_request_execution,
    get_connection,
    get_recent_messages,
    get_user_db_id,
    save_message,
)


def _is_safe_ci_database() -> bool:
    """Allow integration tests only against our dedicated CI database."""
    if os.getenv("CI", "").lower() != "true":
        return False

    if os.getenv("RUN_DATABASE_INTEGRATION_TESTS") != "1":
        return False

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return False

    parsed = urlparse(database_url)

    return (
        parsed.scheme in {"postgres", "postgresql"}
        and parsed.hostname in {"localhost", "127.0.0.1"}
        and parsed.port == 5432
        and parsed.username == "postgres"
        and unquote(parsed.password or "") == "ci-test-password"
        and parsed.path == "/jarvis_test"
    )


pytestmark = pytest.mark.skipif(
    not _is_safe_ci_database(),
    reason=(
        "Integration tests require CI=true, "
        "RUN_DATABASE_INTEGRATION_TESTS=1, "
        "and the dedicated jarvis_test database."
    ),
)


@pytest.fixture
def test_user_id():
    """Create a unique test user and clean up related data afterward."""
    user_id = f"ci-test-{uuid.uuid4().hex}"

    try:
        yield user_id
    finally:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM public.users
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _fetch_execution_for_conversation(conversation_id: int):
    """Return execution fields used to verify real database persistence."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, completed_at, error_message
                FROM public.request_executions
                WHERE conversation_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (conversation_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def test_get_user_db_id_is_idempotent(test_user_id):
    """Repeated calls for one external ID return the same database ID."""
    first_id = get_user_db_id(test_user_id)
    second_id = get_user_db_id(test_user_id)

    assert first_id == second_id


def test_conversation_messages_persist_in_chronological_order(test_user_id):
    """Messages are returned oldest first for conversation history."""
    conversation_id = create_conversation(test_user_id)

    save_message(conversation_id, "user", "Hello JARVIS")
    save_message(
        conversation_id,
        "assistant",
        "Hello! How can I help?",
    )

    assert get_recent_messages(conversation_id) == [
        ("user", "Hello JARVIS"),
        ("assistant", "Hello! How can I help?"),
    ]


def test_recent_messages_respects_limit(test_user_id):
    """Only the newest N messages are returned, in chronological order."""
    conversation_id = create_conversation(test_user_id)

    save_message(conversation_id, "user", "First message")
    save_message(conversation_id, "assistant", "Second message")
    save_message(conversation_id, "user", "Third message")

    assert get_recent_messages(conversation_id, limit=2) == [
        ("assistant", "Second message"),
        ("user", "Third message"),
    ]


def test_message_requires_existing_conversation():
    """PostgreSQL rejects messages with nonexistent conversation IDs."""
    with pytest.raises(psycopg2.IntegrityError):
        save_message(
            -1,
            "user",
            "This message must not be persisted",
        )


def test_new_conversation_has_no_messages(test_user_id):
    """A newly created conversation starts with an empty history."""
    conversation_id = create_conversation(test_user_id)

    assert get_recent_messages(conversation_id) == []


def test_failed_message_insert_does_not_persist_data(test_user_id):
    """A rejected insert leaves existing conversation history unchanged."""
    conversation_id = create_conversation(test_user_id)
    save_message(conversation_id, "user", "Existing valid message")

    with pytest.raises(psycopg2.IntegrityError):
        # The schema requires messages.content to be NOT NULL.
        save_message(conversation_id, "assistant", None)

    assert get_recent_messages(conversation_id) == [
        ("user", "Existing valid message"),
    ]


def test_messages_are_isolated_between_conversations(test_user_id):
    """Messages in one conversation never appear in another's history."""
    first_conversation = create_conversation(test_user_id)
    second_conversation = create_conversation(test_user_id)

    save_message(first_conversation, "user", "First conversation only")
    save_message(second_conversation, "user", "Second conversation only")

    assert get_recent_messages(first_conversation) == [
        ("user", "First conversation only"),
    ]

    assert get_recent_messages(second_conversation) == [
        ("user", "Second conversation only"),
    ]


def test_request_execution_can_be_marked_succeeded(test_user_id):
    """A completed successful execution persists status and completion time."""
    conversation_id = create_conversation(test_user_id)
    execution_id = create_request_execution(conversation_id)

    finish_request_execution(execution_id, status="succeeded")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, completed_at, error_message
                FROM public.request_executions
                WHERE id = %s
                """,
                (execution_id,),
            )
            result = cur.fetchone()
    finally:
        conn.close()

    assert result is not None
    assert result[0] == "succeeded"
    assert result[1] is not None
    assert result[2] is None


def test_request_execution_can_be_marked_failed(test_user_id):
    """A failed execution persists its status, timestamp, and safe error."""
    conversation_id = create_conversation(test_user_id)
    execution_id = create_request_execution(conversation_id)

    finish_request_execution(
        execution_id,
        status="failed",
        error_message="Request processing failed (RuntimeError).",
    )

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, completed_at, error_message
                FROM public.request_executions
                WHERE id = %s
                """,
                (execution_id,),
            )
            result = cur.fetchone()
    finally:
        conn.close()

    assert result is not None
    assert result[0] == "failed"
    assert result[1] is not None
    assert result[2] == "Request processing failed (RuntimeError)."


def test_api_success_persists_answer_and_succeeded_execution(
    test_user_id,
    monkeypatch,
):
    """A successful API request persists both messages and execution state."""
    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        lambda question, model_name: "Integration-test answer",
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/ask",
        json={
            "user_id": test_user_id,
            "question": "Integration-test question",
            "model": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    conversation_id = body["conversation_id"]

    assert get_recent_messages(conversation_id) == [
        ("user", "Integration-test question"),
        ("assistant", "Integration-test answer"),
    ]

    execution = _fetch_execution_for_conversation(conversation_id)
    assert execution is not None
    assert execution[0] == "succeeded"
    assert execution[1] is not None
    assert execution[2] is None


def test_api_gemini_failure_persists_question_and_failed_execution(
    test_user_id,
    monkeypatch,
):
    """A Gemini failure preserves the question and records a failed execution."""

    def fail_gemini(question, model_name):
        raise RuntimeError("Simulated Gemini failure for integration test")

    monkeypatch.setattr(
        ask_route,
        "generate_gemini_response",
        fail_gemini,
    )

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/ask",
        json={
            "user_id": test_user_id,
            "question": "Question must remain stored after failure",
            "model": "gemini-2.5-flash",
        },
    )

    assert response.status_code == 500

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id
                FROM public.conversations AS c
                JOIN public.users AS u ON u.id = c.user_id
                WHERE u.user_id = %s
                ORDER BY c.id DESC
                LIMIT 1
                """,
                (test_user_id,),
            )
            conversation_result = cur.fetchone()
    finally:
        conn.close()

    assert conversation_result is not None
    conversation_id = conversation_result[0]

    assert get_recent_messages(conversation_id) == [
        ("user", "Question must remain stored after failure"),
    ]

    execution = _fetch_execution_for_conversation(conversation_id)
    assert execution is not None
    assert execution[0] == "failed"
    assert execution[1] is not None
    assert execution[2] == "Request processing failed (RuntimeError)."
