"""FastAPI request dependencies for authentication and database sessions."""

import logging
from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)

# Reusable security scheme (Bearer token)
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Dependency deriving the authenticated user from the validated Bearer token.

    Raises HTTP 401 if token is missing, invalid, expired, or user does not exist.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = auth_service.decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Dependency deriving authenticated user if present, or returning None without erroring.

    Used by endpoints like /api/chat that support both anonymous and authenticated usage.
    Handles temporary database unavailability gracefully without crashing.
    """
    if not credentials or not credentials.credentials:
        return None

    user_id = auth_service.decode_access_token(credentials.credentials)
    if not user_id:
        return None

    try:
        return db.query(User).filter(User.id == user_id).first()
    except Exception as exc:
        logger.warning(f"Failed to lookup optional current user from database session: {exc}")
        return None


def verify_ingest_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_ingest_key: Optional[str] = Header(None, alias="X-Ingest-Key"),
    db: Session = Depends(get_db),
) -> bool:
    """Verify authorization for triggering background advisory ingestion.

    Accepts:
    1. Header `X-Ingest-Key` or Bearer token matching `settings.advisory_ingest_secret`
       (or `settings.jwt_secret` if not explicitly configured), OR
    2. A valid JWT access token issued to an authenticated user.

    Raises HTTP 401 Unauthorized if token is missing or invalid.
    """
    token: Optional[str] = None
    if x_ingest_key and x_ingest_key.strip():
        token = x_ingest_key.strip()
    elif credentials and credentials.credentials:
        token = credentials.credentials.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ingestion authorization required. Provide Bearer token or X-Ingest-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Check configured secret key for scheduler / cron job
    expected_secret = settings.advisory_ingest_secret or settings.jwt_secret
    if expected_secret and token == expected_secret:
        return True

    # 2. Check if token is a valid JWT issued to a registered user
    user_id = auth_service.decode_access_token(token)
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return True

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid ingestion authorization token.",
        headers={"WWW-Authenticate": "Bearer"},
    )



