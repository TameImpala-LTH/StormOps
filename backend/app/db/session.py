"""Database engine and session management for PostgreSQL."""

import app.core.compat  # noqa: F401
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

logger = logging.getLogger(__name__)

def get_normalized_database_url(url: str) -> str:
    """Normalize PostgreSQL database URL schemes for psycopg 3 compatibility.

    Render, Heroku, and other cloud providers supply database URLs as
    `postgres://` or `postgresql://`. SQLAlchemy with psycopg 3 requires
    `postgresql+psycopg://`.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


# Configure engine for PostgreSQL with psycopg 3
try:
    _normalized_url = get_normalized_database_url(settings.database_url)
    engine = create_engine(
        _normalized_url,
        pool_pre_ping=True,
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as exc:
    logger.error(f"Failed to create database engine: {exc}")
    engine = None
    SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency providing a transactional database session."""
    if SessionLocal is None:
        raise RuntimeError("Database is not configured or engine failed to initialize.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Check whether PostgreSQL database connection is alive and healthy."""
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(f"Database connection check failed: {exc}")
        return False
