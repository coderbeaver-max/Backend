
import os
from dotenv import load_dotenv

# Loads local .env values when available.
# Railway supplies its own environment variables in production.
load_dotenv()


# -------------------------
# Gemini configuration
# -------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. "
        "Configure it in your local .env or Railway variables."
    )


ALLOWED_MODELS = {
    "gemini-2.5-flash",
    "gemini-1.5-flash",
}


# -------------------------
# PostgreSQL configuration
# -------------------------

# Support both our application variable names and PostgreSQL's
# standard PG* variable names.

DB_HOST = (
    os.getenv("DB_HOST")
    or os.getenv("PGHOST")
)

DB_PORT = (
    os.getenv("DB_PORT")
    or os.getenv("PGPORT")
    or "5432"
)

DB_NAME = (
    os.getenv("DB_NAME")
    or os.getenv("DB_DATABASE")
    or os.getenv("PGDATABASE")
)

DB_USER = (
    os.getenv("DB_USER")
    or os.getenv("PGUSER")
)

DB_PASSWORD = (
    os.getenv("DB_PASSWORD")
    or os.getenv("PGPASSWORD")
)


def get_database_config() -> dict:
    """Return validated PostgreSQL connection settings."""

    settings = {
        "DB_HOST": DB_HOST,
        "DB_PORT": DB_PORT,
        "DB_NAME": DB_NAME,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
    }

    missing = [
        name
        for name, value in settings.items()
        if value is None or not str(value).strip()
    ]

    if missing:
        raise RuntimeError(
            "Missing database configuration: "
            + ", ".join(missing)
        )

    return {
        "host": DB_HOST,
        "port": int(DB_PORT),
        "dbname": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
    }
