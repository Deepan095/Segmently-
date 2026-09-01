"""Segmently FastAPI application entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("segmently")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
    """Render :class:`AppException` as ``{"code", "message"}`` JSON."""
    logger.warning("AppException: %s - %s", exc.code, exc.message)
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "healthy", "app": settings.APP_NAME}


@app.on_event("shutdown")
async def _close_queue_pool() -> None:
    """Close the shared arq Redis pool if the projects module opened one."""
    try:
        from app.workers.queue import close_pool

        await close_pool()
    except Exception:  # noqa: BLE001 - best-effort cleanup
        logger.debug("No arq pool to close")


def _register_routers() -> None:
    """Include module routers that exist.

    Phase 2 agents add router modules under ``app.routers``. Imports are
    wrapped defensively so the app boots with any subset present.
    """
    router_modules = (
        "auth",
        "users",
        "projects",
        "clips",
        "dashboard",
        "admin",
    )
    for name in router_modules:
        module_path = f"app.routers.{name}"
        try:
            module = __import__(module_path, fromlist=["router"])
        except ModuleNotFoundError as exc:
            # The router module itself is genuinely absent - fine during
            # incremental builds. A *dependency* of the module being missing
            # is a real error and is surfaced below.
            if exc.name == module_path:
                logger.info("Router '%s' not present yet - skipping", name)
                continue
            logger.exception("Router '%s' failed to import: %s", name, exc)
            raise
        except Exception:
            logger.exception("Router '%s' failed to import", name)
            raise
        router = getattr(module, "router", None)
        if router is None:
            logger.warning("Module 'app.routers.%s' has no 'router'", name)
            continue
        app.include_router(router, prefix="/api/v1")
        logger.info("Registered router '%s'", name)


_register_routers()
