"""FastAPI request dependencies for authentication and database sessions."""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

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


