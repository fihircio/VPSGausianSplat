from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
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


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
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

