from __future__ import annotations

from contextlib import contextmanager
from urllib.parse import urlparse

from app.config import settings


def _parse_database_url(database_url: str) -> dict[str, object]:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError("DATABASE_URL must use postgresql:// or postgres://")
    return {
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": (parsed.path or "/").lstrip("/"),
    }


@contextmanager
def connect(database_url: str | None = None):
    import pg8000.dbapi

    dsn = database_url or settings.database_url
    if not dsn:
        raise ValueError("DATABASE_URL is not set.")
    conn = pg8000.dbapi.connect(**_parse_database_url(dsn))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
