# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Segmently backend image.
#
# This single image is shared by two docker-compose services:
#   * api    -> runs uvicorn (FastAPI)
#   * worker -> runs the arq media pipeline worker
#
# Because the worker renders clips with FFmpeg, FFmpeg is installed in the
# final stage so it is present for BOTH services.
# ---------------------------------------------------------------------------

# ----- Stage 1: build wheels / install deps into a venv ---------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build-only toolchain for compiling C extensions (psycopg2, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ----- Stage 2: slim runtime ----------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime-only OS deps:
#   * libpq5           -> Postgres client lib for psycopg2
#   * ffmpeg           -> media rendering (worker)
#   * fonts-noto-core  -> caption glyphs for Latin + Tamil/Indic/Arabic/... scripts
#   * fonts-dejavu-core, fontconfig -> fallback + font cache
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 ffmpeg fontconfig fonts-noto-core fonts-dejavu-core \
    && fc-cache -f \
    && rm -rf /var/lib/apt/lists/*

# Bring in the pre-built virtualenv from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Application code (see backend/.dockerignore for what is excluded).
# alembic.ini / alembic/ are copied when present (added by DATABASE-AGENT).
COPY . .

# Run as an unprivileged user. /models is the mount point for the persistent
# whisper/HF model cache (see docker-compose.yml) - appuser must own it.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app \
    && mkdir -p /models && chown appuser:appuser /models
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
