"""Authentication router for user registration, login, and profile retrieval."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new individual user account.

    Enforces email uniqueness, hashes password with bcrypt, and returns an access token.
    """
    normalized_email = payload.email.strip().lower()

    # Check for existing account
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    hashed_pw = auth_service.hash_password(payload.password)
    new_user = User(
        email=normalized_email,
        password_hash=hashed_pw,
        display_name=payload.display_name.strip(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = auth_service.create_access_token(new_user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate an existing user with email and password."""
    normalized_email = payload.email.strip().lower()

    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or not auth_service.verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_service.create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
