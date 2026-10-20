
import os
import time
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
    """Create a unique test user and clean up its related data."""
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
    first_id = get_user_db_id(test_user_id)
    second_id = get_user_db_id(test_user_id)

    assert first_id == second_id


def test_conversation_messages_persist_in_chronological_order(
    test_user_id,
):
    conversation_id = create_conversation(test_user_id)

    save_message(conversation_id, "user", "Hello JARVIS")
    time.sleep(0.02)
    save_message(
        conversation_id,
        "assistant",
        "Hello! How can I help?",
    )

    messages = get_recent_messages(conversation_id)

    assert messages == [
        ("user", "Hello JARVIS"),
        ("assistant", "Hello! How can I help?"),
    ]


def test_recent_messages_respects_limit(test_user_id):
    conversation_id = create_conversation(test_user_id)

    save_message(conversation_id, "user", "First message")
    time.sleep(0.02)
    save_message(conversation_id, "assistant", "Second message")
    time.sleep(0.02)
    save_message(conversation_id, "user", "Third message")

    messages = get_recent_messages(conversation_id, limit=2)

    assert messages == [
        ("assistant", "Second message"),
        ("user", "Third message"),
    ]


def test_message_requires_existing_conversation():
    with pytest.raises(psycopg2.IntegrityError):
        save_message(
            -1,
            "user",
            "This message must not be persisted",
        )
