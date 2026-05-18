"""Engine + session factory."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from repse.config import Settings, get_settings


def make_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.db_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=10,
        future=True,
    )


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def init_db(settings: Settings | None = None) -> None:
    """Idempotent initialization, called from the FastAPI lifespan."""
    global _engine, _SessionLocal
    if _engine is not None:
        return
    _engine = make_engine(settings or get_settings())
    _SessionLocal = make_session_factory(_engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a Session, closing it after the request."""
    if _SessionLocal is None:
        init_db()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_engine() -> Engine:
    if _engine is None:
        init_db()
    assert _engine is not None
    return _engine
