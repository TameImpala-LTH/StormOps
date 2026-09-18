"""Application configuration using pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """WeatherGPT application settings loaded from environment variables."""

    # Application
    app_name: str = "WeatherGPT"
    app_env: str = "development"
    app_debug: bool = True

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Weather API (Open-Meteo as default provider)
    weather_api_key: str = ""
    weather_api_base_url: str = "https://api.open-meteo.com/v1/forecast"

    # Fallback Weather Provider (OpenWeather)
    openweather_api_key: str = ""
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"

    # AI / LLM Provider Configuration (Groq OpenAI-compatible & Whisper)
    ai_provider: str = "groq"
    ai_api_key: str = ""
    ai_model: str = "openai/gpt-oss-120b"
    ai_api_base: str = "https://api.groq.com/openai/v1"
    ai_transcription_model: str = "whisper-large-v3-turbo"

    # Database Configuration (PostgreSQL)
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/stormops"

    # Authentication (JWT & Password Hashing)
    jwt_secret: str = "stormops-hackathon-insecure-default-change-in-env-secret-key-32b"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Official Environmental Advisory Ingestion Configuration
    advisory_enabled: bool = True
    advisory_sachet_feed_url: str = "https://sachet.ndma.gov.in/cap/rss"
    advisory_imd_api_url: str = "https://api.imd.gov.in/v1"
    advisory_imd_api_key: str = ""
    advisory_cpcb_api_url: str = "https://app.cpcbccr.com/caaqm"
    advisory_incois_api_url: str = "https://incois.gov.in/portal/osf"
    advisory_ingestion_interval_seconds: int = 900  # 15 minutes default
    advisory_ingest_secret: str = ""  # Secret token required to trigger ingestion in production

    model_config = {
        "env_file": (
            str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),  # C:\StormOps\.env
            str(Path(__file__).resolve().parent.parent.parent / ".env"),         # C:\StormOps\backend\.env
            ".env",
        ),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
