
import os
from typing import Literal

import psycopg2

from config.settings import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
)


def get_connection():
    """
    Connect to PostgreSQL using either:
    1. DATABASE_URL (Railway or another hosted PostgreSQL provider)
    2. Individual DB_* settings (local development)
    """
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
        raise RuntimeError(
            "Database configuration is incomplete. Set DATABASE_URL "
            "or configure DB_HOST, DB_PORT, DB_NAME, DB_USER, "
            "and DB_PASSWORD."
        )

    return psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def _get_or_create_user_id(cur, user_id: str):
    """
    Get a database user ID or create the user if it does not exist.

    The caller controls the transaction, allowing this operation to
    participate in a larger atomic database operation.
    """
    cur.execute(
        """
        INSERT INTO users (user_id)
        VALUES (%s)
        ON CONFLICT (user_id)
        DO UPDATE SET user_id = EXCLUDED.user_id
        RETURNING id
        """,
        (user_id,),
    )

    result = cur.fetchone()

    if not result:
        raise ValueError("Unable to create or retrieve user")

    return result[0]


def get_user_db_id(user_id: str):
    """Create or retrieve a user and return its database ID."""
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            db_user_id = _get_or_create_user_id(cur, user_id)

        conn.commit()
        return db_user_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def create_conversation(user_id: str):
    """
    Create or retrieve the user and create a conversation atomically.

    If either database operation fails, neither operation is committed.
    """
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            db_user_id = _get_or_create_user_id(cur, user_id)

            cur.execute(
                """
                INSERT INTO conversations (user_id)
                VALUES (%s)
                RETURNING id
                """,
                (db_user_id,),
            )

            result = cur.fetchone()

            if not result:
                raise ValueError("Unable to create conversation")

            conversation_id = result[0]

        conn.commit()
        return conversation_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def save_message(
    conversation_id: int,
    role: str,
    content: str,
):
    """Persist a message and roll back if the insert fails."""
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (
                    conversation_id,
                    role,
                    content
                )
                VALUES (%s, %s, %s)
                """,
                (conversation_id, role, content),
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_recent_messages(
    conversation_id: int,
    limit: int = 10,
):
    """Return the most recent messages in chronological order."""
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
                """,
                (conversation_id, limit),
            )

            rows = cur.fetchall()
            rows.reverse()

            return rows

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def create_request_execution(conversation_id: int) -> int:
    """
    Create a pending execution record for one AI request.

    Returns the new request execution ID.
    """
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.request_executions (
                    conversation_id
                )
                VALUES (%s)
                RETURNING id
                """,
                (conversation_id,),
            )

            result = cur.fetchone()

            if not result:
                raise ValueError(
                    "Unable to create request execution"
                )

            execution_id = result[0]

        conn.commit()
        return execution_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def finish_request_execution(
    execution_id: int,
    status: Literal["succeeded", "failed"],
    error_message: str | None = None,
):
    """
    Finish an execution that is currently pending.

    Only succeeded and failed are valid completion statuses.
    The database enforces the corresponding completed_at requirement.
    """
    if status not in ("succeeded", "failed"):
        raise ValueError(
            "Execution status must be 'succeeded' or 'failed'."
        )

    if status == "succeeded":
        error_message = None
    elif not error_message:
        error_message = "Request failed; no error detail was recorded."

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.request_executions
                SET
                    status = %s,
                    error_message = %s,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status = 'pending'
                RETURNING id
                """,
                (status, error_message, execution_id),
            )

            result = cur.fetchone()

            if not result:
                raise ValueError(
                    "Request execution was not found or "
                    "is no longer pending."
                )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
