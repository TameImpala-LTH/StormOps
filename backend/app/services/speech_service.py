"""Audio speech-to-text transcription service using Groq Whisper endpoint."""

import logging
from typing import Optional, Tuple
import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.services.multilingual_service import multilingual_service

logger = logging.getLogger(__name__)

# Supported audio MIME types and extensions for MediaRecorder uploads
SUPPORTED_AUDIO_TYPES = {
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/ogg",
    "audio/ogg;codecs=opus",
    "audio/wav",
    "audio/x-wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/m4a",
    "audio/mp4",
}


class SpeechService:
    """Service providing audio transcription via Groq Whisper audio transcriptions endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.ai_api_key
        self.model = model or getattr(settings, "ai_transcription_model", "whisper-large-v3-turbo")
        self.api_base = (api_base or settings.ai_api_base or "https://api.groq.com/openai/v1").rstrip("/")
        self._client = client

    @property
    def is_configured(self) -> bool:
        """Return True if Groq API key is configured."""
        return bool(self.api_key and self.api_key.strip())

    def validate_audio(self, content_type: Optional[str], filename: Optional[str], content_bytes: bytes) -> str:
        """Validate uploaded audio MIME type, extension, and content size."""
        if not content_bytes or len(content_bytes) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Couldn't hear anything. Try again.",
            )

        ct = (content_type or "").split(";")[0].strip().lower()
        if ct and ct not in {t.split(";")[0] for t in SUPPORTED_AUDIO_TYPES}:
            # Check filename extension as fallback
            fn = (filename or "").lower()
            if not any(fn.endswith(ext) for ext in [".webm", ".ogg", ".wav", ".mp3", ".m4a", ".mp4"]):
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported audio format '{content_type}'. Please record using webm, ogg, or wav.",
                )

        upload_name = filename or "audio.webm"
        if not any(upload_name.lower().endswith(ext) for ext in [".webm", ".ogg", ".wav", ".mp3", ".m4a", ".mp4"]):
            upload_name = "audio.webm"

        return upload_name

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Transcribe audio bytes using Groq Whisper endpoint.

        Returns (transcribed_text, language_code).
        """
        if not self.is_configured:
            logger.warning("Speech transcription failed: Groq API key is not configured.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Voice transcription is not configured. Please configure the Groq API key.",
            )

        upload_filename = self.validate_audio(content_type, filename, audio_bytes)

        # Map language parameter: Auto/empty -> None; explicit 'en'/'hi'/'bn'/'ta'/'te'/'mr'
        target_lang = None
        if language and language.strip().lower() not in ("auto", "none", ""):
            normalized = multilingual_service.normalize_language(language)
            if normalized in ("en", "hi", "bn", "ta", "te", "mr"):
                target_lang = normalized

        url = f"{self.api_base}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        # Groq Whisper accepts multipart/form-data with file, model, response_format, temperature, and optional language
        mime_type = content_type or "audio/webm"
        files = {
            "file": (upload_filename, audio_bytes, mime_type),
        }
        data = {
            "model": self.model,
            "response_format": "json",
            "temperature": "0",
        }
        if target_lang:
            data["language"] = target_lang

        timeout = httpx.Timeout(30.0, connect=10.0)

        try:
            if self._client:
                response = await self._client.post(url, headers=headers, data=data, files=files, timeout=timeout)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, data=data, files=files, timeout=timeout)

            if response.status_code in (401, 403):
                logger.error(
                    f"Groq transcription authentication error {response.status_code}: {response.text[:300]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Voice transcription authentication failed.",
                )
            elif response.status_code == 429:
                logger.error(
                    f"Groq transcription quota/rate limit error {response.status_code}: {response.text[:300]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Voice transcription quota is unavailable. Please check your Groq API usage or limits.",
                )
            elif response.status_code >= 500:
                logger.error(
                    f"Groq transcription provider error {response.status_code}: {response.text[:300]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Voice transcription service is unavailable.",
                )
            elif response.status_code != 200:
                logger.error(
                    f"Groq transcription provider error {response.status_code}: {response.text[:300]}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Couldn't transcribe that recording. Please try again.",
                )

            res_json = response.json()
            raw_text = res_json.get("text", "").strip()

            if not raw_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Couldn't hear anything. Try again.",
                )

            # Detect or confirm language of transcript
            resolved_lang = target_lang or multilingual_service.detect_language(raw_text)

            return raw_text, resolved_lang

        except httpx.TimeoutException:
            logger.error("Groq transcription request timed out.")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Voice transcription timed out. Please try again.",
            )
        except httpx.RequestError as exc:
            logger.error(f"Network error calling Groq transcription provider: {exc}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Voice transcription service is unavailable.",
            )


speech_service = SpeechService()
