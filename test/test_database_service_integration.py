
"""Integration tests for the JARVIS PostgreSQL persistence layer.

These tests are restricted to the dedicated GitHub Actions jarvis_test
database. Never weaken the safety guard to run them against production.
"""

import os
import uuid
from urllib.parse import unquote, urlparse

import psycopg2
import pytest

from Services.database_service import (
    create_conversation,
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
