"""Unit and regression tests for Groq Whisper speech transcription endpoint, validation, language mapping, and error handling."""

import app.core.compat  # noqa: F401
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import httpx
import pytest

from app.main import app
from app.services.speech_service import speech_service

client = TestClient(app)

# 120 bytes of dummy webm audio
DUMMY_AUDIO = b"\x1a\x45\xdf\xa3" + b"\x00" * 120


def test_transcribe_missing_api_key():
    """Verify endpoint returns 503 if Groq API key is missing."""
    with patch.object(speech_service, "api_key", ""):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm")},
            data={"language": "en"},
        )
        assert response.status_code == 503
        assert "configure the Groq API key" in response.json()["detail"]


def test_transcribe_empty_file():
    """Verify endpoint rejects empty or extremely short audio."""
    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", b"too_short", "audio/webm")},
            data={"language": "en"},
        )
        assert response.status_code == 400
        assert "Couldn't hear anything" in response.json()["detail"]


def test_transcribe_unsupported_audio_type():
    """Verify endpoint rejects unsupported audio formats."""
    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("document.pdf", b"a" * 200, "application/pdf")},
            data={"language": "en"},
        )
        assert response.status_code == 415
        assert "Unsupported audio format" in response.json()["detail"]


@patch("app.services.speech_service.httpx.AsyncClient.post")
def test_transcribe_success_english(mock_post):
    """Verify successful English speech transcription using Groq Whisper response format."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "What is the weather in Kolkata today?"}
    mock_post.return_value = mock_resp

    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm")},
            data={"language": "en"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "What is the weather in Kolkata today?"
        assert data["language"] == "en"


@patch("app.services.speech_service.httpx.AsyncClient.post")
def test_transcribe_success_hindi(mock_post):
    """Verify successful Hindi speech transcription with Devanagari script."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "कोलकाता में आज मौसम कैसा है?"}
    mock_post.return_value = mock_resp

    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm;codecs=opus")},
            data={"language": "hi"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "कोलकाता में आज मौसम कैसा है?"
        assert data["language"] == "hi"


@patch("app.services.speech_service.httpx.AsyncClient.post")
def test_transcribe_success_bengali(mock_post):
    """Verify successful Bengali speech transcription with Bengali script."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "কলকাতার আজকের আবহাওয়া কেমন?"}
    mock_post.return_value = mock_resp

    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm")},
            data={"language": "bn"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "কলকাতার আজকের আবহাওয়া কেমন?"
        assert data["language"] == "bn"


@patch("app.services.speech_service.httpx.AsyncClient.post")
def test_transcribe_quota_error(mock_post):
    """Verify Groq quota/rate limit 429 maps to friendly error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit reached"
    mock_post.return_value = mock_resp

    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm")},
            data={"language": "en"},
        )
        assert response.status_code == 502
        assert "quota is unavailable" in response.json()["detail"]


@patch("app.services.speech_service.httpx.AsyncClient.post")
def test_transcribe_auth_error(mock_post):
    """Verify Groq 401/403 maps to authentication failure error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Invalid API Key"
    mock_post.return_value = mock_resp

    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm")},
            data={"language": "en"},
        )
        assert response.status_code == 502
        assert "authentication failed" in response.json()["detail"]


@patch("app.services.speech_service.httpx.AsyncClient.post")
def test_transcribe_provider_error(mock_post):
    """Verify provider 500 error maps to friendly 502 message."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Provider Error"
    mock_post.return_value = mock_resp

    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm")},
            data={"language": "en"},
        )
        assert response.status_code == 502
        assert "Voice transcription service is unavailable" in response.json()["detail"]


@patch("app.services.speech_service.httpx.AsyncClient.post")
def test_transcribe_timeout_error(mock_post):
    """Verify provider timeout maps to 504 gateway timeout."""
    mock_post.side_effect = httpx.TimeoutException("Timeout")

    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm")},
            data={"language": "en"},
        )
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]


@patch("app.services.speech_service.httpx.AsyncClient.post")
def test_transcribe_empty_provider_result(mock_post):
    """Verify empty text from provider raises friendly error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "   "}
    mock_post.return_value = mock_resp

    with patch.object(speech_service, "api_key", "mock-key"):
        response = client.post(
            "/api/speech/transcribe",
            files={"file": ("audio.webm", DUMMY_AUDIO, "audio/webm")},
            data={"language": "en"},
        )
        assert response.status_code == 400
        assert "Couldn't hear anything" in response.json()["detail"]
