"""Pydantic schemas for audio speech-to-text transcription."""

from typing import Optional
from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    """Schema for successful audio transcription response."""

    text: str = Field(..., description="Transcribed text from user audio")
    language: Optional[str] = Field("en", description="Resolved or provided language code ('en', 'hi', 'bn', 'ta', 'te', 'mr')")
