import psycopg2

from config.settings import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD
)


# =========================
# DB CONNECTION
# =========================
def get_connection():

    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


# =========================
# GET OR CREATE USER DB ID
# =========================
def get_user_db_id(user_id: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) 
                DO UPDATE SET user_id = EXCLUDED.user_id
                RETURNING id
                """,
                (user_id,)
            )
            
            result = cur.fetchone()
            
            if not result:
                raise ValueError("Unable to create or retrieve user")
                
            conn.commit()
            return result[0]
            
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =========================
# CREATE CONVERSATION
# =========================
def create_conversation(
    user_id: str
):

    db_user_id = get_user_db_id(
        user_id
    )

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO conversations (
                    user_id
                )
                VALUES (%s)
                RETURNING id
                """,
                (db_user_id,)
            )

            conversation_id = cur.fetchone()[0]

            conn.commit()

            return conversation_id

    finally:

        conn.close()


# =========================
# SAVE MESSAGE
# =========================
def save_message(
    conversation_id: int,
    role: str,
    content: str
):

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
                (
                    conversation_id,
                    role,
                    content
                )
            )

            conn.commit()

    finally:

        conn.close()


# =========================
# GET RECENT MESSAGES
# =========================
def get_recent_messages(
    conversation_id: int,
    limit: int = 10
):

    conn = get_connection()

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (
                    conversation_id,
                    limit
                )
            )

            rows = cur.fetchall()

            rows.reverse()

            return rows

    finally:

        conn.close()