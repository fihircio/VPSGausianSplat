from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base  # noqa: F401
from backend.utils.config import get_settings

# ---------------------------------------------------------------------------
# Lazy engine / session factory
# ---------------------------------------------------------------------------
# We intentionally defer engine creation until first use.  This means
# importing this module does NOT open a database connection, which allows
# FastAPI's TestClient to apply dependency overrides before any I/O happens.

_engine: Any = None
_SessionLocal: Any = None


def _apply_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Tune a file-backed SQLite connection for the API + pipeline thread mix.

    The scene pipeline runs in a daemon thread while FastAPI request handlers
    read and write the same file, so SQLite's defaults would surface as
    ``database is locked`` errors mid-processing:

    * ``journal_mode=WAL`` lets readers and the single writer run concurrently.
    * ``busy_timeout`` waits for a competing writer instead of failing at once.
    * ``synchronous=NORMAL`` is the safe pairing with WAL on a dev workstation.
    * ``foreign_keys=ON`` matches the referential behaviour Postgres gives us.

    ``:memory:`` databases answer ``memory`` for journal_mode and ignore the
    rest, so this is harmless for tests.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        database_url = settings.database_url
        _engine = create_engine(database_url, pool_pre_ping=True)
        if database_url.startswith("sqlite"):
            event.listen(_engine, "connect", _apply_sqlite_pragmas)
        _SessionLocal = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _engine


def _get_session_local():
    _get_engine()  # ensure engine + factory are created
    return _SessionLocal


# Keep a module-level alias so code that does `from backend.utils.db import
# SessionLocal` still works (it will resolve lazily on first call).
class _LazySessionLocal:
    """Proxy that forwards __call__ to the real session factory."""

    def __call__(self, **kwargs):
        return _get_session_local()(**kwargs)

    def __getattr__(self, item):
        return getattr(_get_session_local(), item)


SessionLocal = _LazySessionLocal()


def init_db() -> None:
    Base.metadata.create_all(bind=_get_engine())


def get_db() -> Generator[Session, None, None]:
    db = _get_session_local()()
    try:
        yield db
    finally:
        db.close()

