from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import EnvSettingsSource
from pydantic import field_validator, Field
from typing import Optional, Any, Dict
from pathlib import Path
from dotenv import load_dotenv
import os
import json

# Find and load .env from root (two levels up from this file)
# This file is at: backend/app/core/config.py
# Root is at: .env
config_file_dir = Path(__file__).parent  # backend/app/core
backend_dir = config_file_dir.parent  # backend/app
project_root = backend_dir.parent.parent  # project root (ai-transcriber)
env_path = project_root / ".env"

# Load from root .env if it exists
if env_path.exists():
    load_dotenv(env_path, override=False)
else:
    # Fallback: try loading from current working directory
    load_dotenv(override=False)


class CustomEnvSettingsSource(EnvSettingsSource):
    """Custom environment settings source that handles comma-separated lists."""

    def prepare_field_value(self, field_name: str, field, value: Any, value_is_complex: bool) -> Any:
        # Handle CORS_ORIGINS specially: don't try to JSON decode comma-separated strings
        if field_name == "CORS_ORIGINS" and isinstance(value, str):
            value = value.strip()
            # If it looks like JSON, let parent handle it
            if value.startswith('['):
                return super().prepare_field_value(field_name, field, value, value_is_complex)
            # Otherwise, treat as comma-separated and mark as not complex
            return value
        return super().prepare_field_value(field_name, field, value, value_is_complex)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=True,
    )

    # App Config
    APP_NAME: str = "AI Transcriber"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:4173"],
        description="Comma-separated or JSON array of allowed CORS origins"
    )

    # Database
    DATABASE_URL: Optional[str] = None  # Auto-detected: sqlite by default, set for PostgreSQL

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB_CACHE: int = 2
    REDIS_DB_CELERY: int = 0
    REDIS_DB_CELERY_RESULT: int = 1
    REDIS_REQUIRED: bool = False
    USE_SQLITE_BROKER: bool = True

    # ML Configuration
    # OPTIMIZATION: Use distil-large-v3 by default (50% faster, slight accuracy drop)
    PRELOAD_MODELS: str = "base,distil-large-v3"
    # TRANSCRIPTION BACKENDS
    ENABLED_BACKENDS: str = "faster-whisper,whisper-cpp"  # Comma-separated list of enabled backends
    WHISPER_BACKEND: str = "faster-whisper"  # Default backend to use (must be in ENABLED_BACKENDS)
    WHISPER_MODEL_SIZE: str = "distil-large-v3"  # Default model size

    # OMP Optimization for CPU inference
    # 4-8 threads usually optimal for faster-whisper on M-series chips
    OMP_NUM_THREADS: int = 4

    # Whisper.cpp configuration
    WHISPER_CPP_AUTO_SETUP: bool = True  # Set to True to auto-compile on startup
    WHISPER_CPP_PATH: Optional[str] = None

    # LLM
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_MODEL: str = "llama3:8b"
    TTL_LLM_CONTEXT: int = 86400  # 24 hours
    TTL_VOCAB_HOTWORDS: int = 3600  # 1 hour

    # AUDIO
    SAMPLE_RATE: int = 16000
    MAX_FILE_SIZE_MB: int = 500

    # Whisper.cpp configuration
    WHISPER_CPP_AUTO_SETUP: bool = False
    WHISPER_CPP_PATH: Optional[str] = None

    # Speaker Diarization
    HUGGINGFACE_TOKEN: Optional[str] = None
    ENABLE_SPEAKER_DIARIZATION: bool = True

    # TRANSCRIPTION PERFORMANCE TUNING
    # VAD (Voice Activity Detection) parameters - lower values = faster segmentation
    VAD_MIN_SILENCE_DURATION_MS: int = 100  # Default: 100ms (was 500ms, too slow)
    VAD_MIN_SPEECH_DURATION_MS: int = 100   # Minimum speech chunk duration

    # Transcription accuracy vs speed trade-off
    TRANSCRIBE_BEAM_SIZE: int = 5           # Was 10 (slower). 5 = good balance
    TRANSCRIBE_BEST_OF: int = 5             # Was 10 (slower). 5 = good balance
    TRANSCRIBE_TEMPERATURE: float = 0.0     # Deterministic output

    # Context extraction optimization
    SKIP_CONTEXT_EXTRACTION: bool = False   # Set True to disable 2-pass transcription
    CONTEXT_MIN_SPEECH_LENGTH: int = 10     # Min words to trigger context extraction

    # Audio preprocessing
    AUDIO_CONVERT_ALWAYS: bool = False      # Set True to force FFmpeg conversion on all files

    # APP METADATA
    PROJECT_NAME: str = "AI Transcriber"
    VERSION: str = "0.1.0"

    # CELERY TASK CONFIGURATION
    TASK_MAX_RETRIES: int = 3
    TASK_RETRY_BACKOFF_BASE: int = 2
    TASK_RETRY_BACKOFF_MAX: int = 600
    TASK_TIME_LIMIT: int = 3600

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string, JSON array, or list."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # Try parsing as JSON first
            if v.startswith('['):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Fall back to comma-separated parsing
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Override settings sources to use custom env source."""
        return (
            init_settings,
            CustomEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

# Initialize settings (reads from os.environ which was populated by load_dotenv)
settings = Settings()

# Auto-Correction Metadata Markers
# These are section headers that the auto-correction LLM adds when explaining its changes
# They should be stripped from the transcript text before displaying to users
AUTO_CORRECTION_METADATA_MARKERS = [
    'Corrected errors include:',
    'Explanations:',
    'Corrections made:',
    'Changes made:',
    'I only performed corrections',
    'I made the following corrections:',
    'Note:',  # Generic note prefix used by auto-correction service
]
