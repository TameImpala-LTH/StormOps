"""Pydantic schemas for authentication and user accounts."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Schema for new user registration."""

    email: EmailStr = Field(..., description="Valid user email address")
    password: str = Field(..., min_length=6, max_length=128, description="User plaintext password")
    display_name: str = Field(..., min_length=1, max_length=100, description="User public display name")


class LoginRequest(BaseModel):
    """Schema for user login credentials."""

    email: EmailStr = Field(..., description="Registered user email")
    password: str = Field(..., min_length=1, description="User password")


class UserResponse(BaseModel):
    """Public representation of a user profile (never exposing password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    """Authentication token response after successful registration or login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
