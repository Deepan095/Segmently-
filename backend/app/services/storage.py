"""S3-compatible object storage client (MinIO in dev, S3 in prod).

Thin wrapper around a lazily-constructed ``boto3`` client built from
``app.config.settings``. ``boto3`` is imported inside the factory so that
importing this module (and therefore the FastAPI app) never requires the
dependency to be installed - only actually touching storage does.

Signed-URL helpers live here too (``media_url.py`` re-exports them).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any, BinaryIO

from app.config import settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mypy_boto3_s3 import S3Client
else:  # pragma: no cover
    S3Client = Any

logger = logging.getLogger("segmently.services.storage")


class StorageError(RuntimeError):
    """Raised when an object-storage operation fails."""


def _build_client(endpoint_url: str | None) -> "S3Client":
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise StorageError(
            "boto3 is not installed - add it to requirements and reinstall"
        ) from exc

    cfg = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path" if settings.STORAGE_FORCE_PATH_STYLE else "auto"},
        retries={"max_attempts": 3, "mode": "standard"},
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        aws_access_key_id=settings.STORAGE_ACCESS_KEY or None,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY or None,
        region_name=settings.STORAGE_REGION,
        config=cfg,
    )


@lru_cache(maxsize=1)
def get_client() -> "S3Client":
    """Cached boto3 client for server-side operations (uses the internal endpoint)."""
    return _build_client(settings.STORAGE_ENDPOINT_URL)


@lru_cache(maxsize=1)
def get_presign_client() -> "S3Client":
    """Cached boto3 client used only to sign browser-facing URLs.

    Signs against ``STORAGE_PUBLIC_ENDPOINT_URL`` so the host in the returned
    URL is reachable from the user's browser (not the Docker-internal name).
    """
    public = settings.STORAGE_PUBLIC_ENDPOINT_URL or settings.STORAGE_ENDPOINT_URL
    return _build_client(public)


def _bucket() -> str:
    return settings.STORAGE_BUCKET


def put_object(
    key: str,
    body: bytes | BinaryIO,
    *,
    content_type: str | None = None,
    metadata: dict[str, str] | None = None,
) -> str:
    """Upload *body* to *key*. Returns the key."""
    extra: dict[str, Any] = {}
    if content_type:
        extra["ContentType"] = content_type
    if metadata:
        extra["Metadata"] = metadata
    try:
        get_client().put_object(Bucket=_bucket(), Key=key, Body=body, **extra)
    except Exception as exc:  # noqa: BLE001 - surface a uniform error
        raise StorageError(f"put_object failed for {key}: {exc}") from exc
    logger.info("Stored object %s", key)
    return key


def upload_file(local_path: str, key: str, *, content_type: str | None = None) -> str:
    """Upload a file from the local filesystem to *key*."""
    extra = {"ContentType": content_type} if content_type else None
    try:
        get_client().upload_file(
            local_path, _bucket(), key, ExtraArgs=extra or None
        )
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"upload_file failed for {key}: {exc}") from exc
    return key


def download_file(key: str, local_path: str) -> str:
    """Download *key* to *local_path* on the local filesystem."""
    try:
        get_client().download_file(_bucket(), key, local_path)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"download_file failed for {key}: {exc}") from exc
    return local_path


def get_object_stream(key: str) -> Any:
    """Return a streaming body for *key* (``.read()``/iterable)."""
    try:
        return get_client().get_object(Bucket=_bucket(), Key=key)["Body"]
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"get_object failed for {key}: {exc}") from exc


def object_exists(key: str) -> bool:
    """Return ``True`` if *key* exists in the bucket."""
    try:
        get_client().head_object(Bucket=_bucket(), Key=key)
        return True
    except Exception:  # noqa: BLE001 - any error means "treat as absent"
        return False


def delete_key(key: str) -> None:
    """Delete a single object. No error if it is already gone."""
    try:
        get_client().delete_object(Bucket=_bucket(), Key=key)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"delete_key failed for {key}: {exc}") from exc
    logger.info("Deleted object %s", key)


def delete_prefix(prefix: str) -> int:
    """Delete every object under *prefix*. Returns the count removed."""
    client = get_client()
    bucket = _bucket()
    removed = 0
    try:
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            contents = page.get("Contents") or []
            if not contents:
                continue
            objects = [{"Key": obj["Key"]} for obj in contents]
            client.delete_objects(Bucket=bucket, Delete={"Objects": objects})
            removed += len(objects)
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"delete_prefix failed for {prefix}: {exc}") from exc
    logger.info("Deleted %d objects under %s", removed, prefix)
    return removed


def generate_presigned_get(key: str, expires: int | None = None) -> str:
    """Return a time-limited GET URL for *key*."""
    ttl = expires or settings.SIGNED_URL_EXPIRE_SECONDS
    try:
        return get_presign_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": key},
            ExpiresIn=ttl,
        )
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"presigned GET failed for {key}: {exc}") from exc


def generate_presigned_put(
    key: str,
    expires: int | None = None,
    *,
    content_type: str | None = None,
) -> str:
    """Return a time-limited PUT URL for a direct browser upload to *key*."""
    ttl = expires or settings.SIGNED_URL_EXPIRE_SECONDS
    params: dict[str, Any] = {"Bucket": _bucket(), "Key": key}
    if content_type:
        params["ContentType"] = content_type
    try:
        return get_presign_client().generate_presigned_url(
            "put_object", Params=params, ExpiresIn=ttl
        )
    except Exception as exc:  # noqa: BLE001
        raise StorageError(f"presigned PUT failed for {key}: {exc}") from exc
