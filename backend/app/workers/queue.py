"""arq queue helpers shared by routers and other modules.

``arq`` is imported lazily so importing this module (and the FastAPI app)
never requires the dependency to be installed. Routers call
:func:`enqueue` to schedule pipeline work; they must never do the work
inline.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.config import settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from arq.connections import ArqRedis

logger = logging.getLogger("segmently.workers.queue")

_pool: "ArqRedis | None" = None


def redis_settings() -> Any:
    """Return an ``arq`` ``RedisSettings`` built from ``settings.REDIS_URL``."""
    from arq.connections import RedisSettings

    return RedisSettings.from_dsn(settings.REDIS_URL)


async def get_pool() -> "ArqRedis":
    """Return a lazily-created, process-wide arq Redis pool."""
    global _pool
    if _pool is None:
        from arq import create_pool

        _pool = await create_pool(redis_settings())
        logger.info("Created arq redis pool")
    return _pool


async def close_pool() -> None:
    """Close the shared pool (call on app shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def enqueue(job_name: str, *args: Any, **kwargs: Any) -> str | None:
    """Enqueue ``job_name`` on the pipeline queue.

    Returns the arq job id, or ``None`` if arq deduplicated the job.
    """
    pool = await get_pool()
    job = await pool.enqueue_job(job_name, *args, **kwargs)
    if job is None:
        logger.warning("arq did not enqueue '%s' (already queued?)", job_name)
        return None
    logger.info("Enqueued '%s' as %s", job_name, job.job_id)
    return job.job_id
