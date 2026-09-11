"""Audio speech transcription endpoint."""

from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile

from app.schemas.speech import TranscriptionResponse
from app.services.speech_service import speech_service

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Recorded audio file (webm, ogg, wav)"),
    language: Optional[str] = Form(None, description="Optional target language hint ('en', 'hi', 'bn', 'ta', 'te', 'mr', or 'auto')"),
):
    """Transcribe user-recorded audio stream into plain text.

    Accepts multipart/form-data audio from browser MediaRecorder.
    Returns transcribed plain text and detected/confirmed language code.
    """
    audio_bytes = await file.read()
    text, resolved_lang = await speech_service.transcribe_audio(
        audio_bytes=audio_bytes,
        filename=file.filename,
        content_type=file.content_type,
        language=language,
    )
    return TranscriptionResponse(text=text, language=resolved_lang)
