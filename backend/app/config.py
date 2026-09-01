"""Application settings loaded from environment / .env file."""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("segmently.config")

# Sentinel values that ship in this file. They are fine for local dev but must
# never reach a non-DEBUG deployment.
_INSECURE_DEFAULTS: dict[str, str] = {
    "SECRET_KEY": "change-me-in-production",
    "ADMIN_PASSWORD": "change-me-admin",
}


class Settings(BaseSettings):
    """Typed application configuration.

    Values are read from environment variables, falling back to a local
    ``.env`` file. Never hardcode secrets - override via the environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- App ---
    APP_NAME: str = "Segmently"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # --- Database ---
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/segmently"

    # --- Auth ---
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # --- Frontend / CORS ---
    FRONTEND_URL: str = "http://localhost:3000"
    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    )

    # --- Object storage (S3-compatible / MinIO in dev) ---
    STORAGE_ENDPOINT_URL: str = "http://localhost:9000"
    # Endpoint used ONLY to sign browser-facing URLs. In the compose stack the
    # API talks to "http://minio:9000" (internal) but the browser must use
    # "http://localhost:9000". Empty -> fall back to STORAGE_ENDPOINT_URL.
    STORAGE_PUBLIC_ENDPOINT_URL: str = ""
    STORAGE_BUCKET: str = "segmently-media"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""

    # --- Worker / queue ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- AI pipeline ---
    # Transcription: "local" = faster-whisper on the worker CPU (no API cost,
    # slower); "openai" = OpenAI audio API (fast, ~$0.006/min, needs a key).
    TRANSCRIPTION_BACKEND: str = "local"
    WHISPER_MODEL: str = "base"  # tiny | base | small | medium | large-v3 (local only)
    WHISPER_DEVICE: str = "cpu"  # "cuda" if the worker has an NVIDIA GPU
    WHISPER_COMPUTE_TYPE: str = "int8"  # "float16" on GPU
    OPENAI_TRANSCRIBE_MODEL: str = "whisper-1"
    # Segment detection (app.services.segmentation) uses the OpenAI Chat API.
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    # How many clips to aim for, and the hard cap. Long videos are split into
    # windows of SEGMENT_WINDOW_SECONDS so clips are spread across the source.
    SEGMENTS_TARGET: int = 6
    SEGMENTS_MAX: int = 10
    SEGMENT_WINDOW_SECONDS: int = 600
    # Legacy Anthropic settings - unused since segmentation moved to OpenAI.
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-5"

    # --- Media pipeline / storage (Module 2) ---
    STORAGE_REGION: str = "us-east-1"
    STORAGE_FORCE_PATH_STYLE: bool = True
    SIGNED_URL_EXPIRE_SECONDS: int = 3600
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024 * 1024  # 5 GiB
    MAX_SOURCE_DURATION_SECONDS: int = 4 * 60 * 60  # cap source length for MVP cost/latency
    ALLOWED_UPLOAD_CONTENT_TYPES: list[str] = Field(
        default_factory=lambda: [
            "video/mp4",
            "video/quicktime",
            "video/x-matroska",
            "video/webm",
            "video/x-msvideo",
            "video/mpeg",
        ]
    )
    FFMPEG_BINARY: str = "ffmpeg"
    FFPROBE_BINARY: str = "ffprobe"
    FFMPEG_PRESET: str = "superfast"  # x264 speed/size trade-off for clip renders
    YTDLP_MAX_HEIGHT: int = 720  # cap yt-dlp source resolution (clips are 1080 wide)
    # Netscape-format cookies.txt for YouTube etc. (datacenter IPs get bot-blocked
    # without one). Mounted into the worker; blank = no cookies.
    YTDLP_COOKIES_FILE: str = "/cookies/youtube.txt"
    # "fit" = whole frame over a blurred fill (screen recordings, slides - nothing
    # is cropped out); "crop" = zoom + centre-crop (best for talking heads).
    RENDER_MODE: str = "fit"

    # --- B-roll (auto stock-footage cutaways) ---
    BROLL_ENABLED: bool = False           # needs PEXELS_API_KEY; opt-in
    PEXELS_API_KEY: str = ""              # https://www.pexels.com/api/ (free)
    BROLL_MAX_PER_CLIP: int = 3
    BROLL_MIN_SECONDS: float = 2.5
    BROLL_MAX_SECONDS: float = 5.0
    BROLL_MAX_COVERAGE: float = 0.45      # cap total b-roll time as a fraction of the clip
    SSRF_ALLOW_PRIVATE: bool = False  # set True only for local dev against internal hosts
    MEDIA_WORK_DIR: str = "/tmp/segmently"

    # --- Seed admin (used by app.auth.seed / scripts/seed.py) ---
    ADMIN_EMAIL: str = "admin@segmently.dev"
    ADMIN_PASSWORD: str = "change-me-admin"

    @model_validator(mode="after")
    def _reject_insecure_defaults_in_prod(self) -> "Settings":
        """Refuse to boot with shipped sentinel secrets when DEBUG is off."""
        offenders = [
            name
            for name, sentinel in _INSECURE_DEFAULTS.items()
            if getattr(self, name) == sentinel
        ]
        if "password@" in self.DATABASE_URL:
            offenders.append("DATABASE_URL")
        if offenders and not self.DEBUG:
            raise ValueError(
                "Insecure default value(s) for "
                f"{', '.join(offenders)}. Set real values via the environment "
                "or run with DEBUG=true for local development."
            )
        if offenders:
            logger.warning(
                "Running with insecure default(s): %s - DEBUG mode only.",
                ", ".join(offenders),
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()


settings: Settings = get_settings()
