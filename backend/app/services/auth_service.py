"""Authentication service providing secure password hashing and JWT token operations."""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional
import bcrypt
import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Service handling password cryptography and JWT token lifecycles."""

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using bcrypt with a salt."""
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pwd_bytes, salt)
        return hashed.decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plaintext password against a stored bcrypt hash."""
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception as exc:
            logger.warning(f"Password verification encountered error: {exc}")
            return False

    def create_access_token(self, subject: str, expires_delta: Optional[timedelta] = None) -> str:
        """Create a signed JWT access token for a user subject (user ID)."""
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=settings.access_token_expire_minutes)

        payload = {
            "sub": str(subject),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    def decode_access_token(self, token: str) -> Optional[str]:
        """Decode and validate a JWT access token, returning the subject (user ID) or None."""
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            return payload.get("sub")
        except jwt.PyJWTError as exc:
            logger.debug(f"JWT validation failed: {exc}")
            return None


auth_service = AuthService()
