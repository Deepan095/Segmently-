"""arq worker entrypoint.

Run with::

    arq app.workers.settings.WorkerSettings

(this is the command docker-compose's ``worker`` service uses).
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.workers.pipeline import (
    run_download,
    run_render,
    run_segment,
    run_transcribe,
)
from app.workers.queue import redis_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("segmently.workers")


async def on_startup(ctx: dict[str, Any]) -> None:
    """Warm up shared resources (DB engine, storage client)."""
    logger.info("Worker starting - model=%s whisper=%s", settings.OPENAI_MODEL, settings.WHISPER_MODEL)
    try:
        from app.database import engine

        with engine.connect() as conn:  # fail fast if the DB is unreachable
            conn.exec_driver_sql("SELECT 1")
        ctx["db_ready"] = True
    except Exception as exc:  # noqa: BLE001 - log, keep running for retries
        logger.warning("DB not reachable at startup: %s", exc)
        ctx["db_ready"] = False


async def on_shutdown(ctx: dict[str, Any]) -> None:
    """Release shared resources."""
    logger.info("Worker shutting down")
    try:
        from app.database import engine

        engine.dispose()
    except Exception:  # noqa: BLE001
        pass


class WorkerSettings:
    """arq ``WorkerSettings`` for the Segmently media pipeline."""

    functions = [run_download, run_transcribe, run_segment, run_render]
    redis_settings = redis_settings()
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_tries = 2
    # Blocking work runs via asyncio.to_thread; cap concurrency so a small VPS
    # isn't running several FFmpeg renders at once.
    max_jobs = int(settings.WORKER_MAX_JOBS)
    job_timeout = 60 * 60  # 1h - long videos + whisper + ffmpeg
    keep_result = 60 * 60 * 24
