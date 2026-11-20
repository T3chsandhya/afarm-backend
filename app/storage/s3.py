"""Upload media to Amazon S3; serve via CloudFront URL stored in the database."""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

from app.config import get_settings
from app.storage.base import (
    ALLOWED_IMAGE_EXT,
    ALLOWED_VIDEO_EXT,
    build_key,
    validate_ext,
)
from app.storage.optimize import optimize_image_bytes

logger = logging.getLogger("storage.s3")

__all__ = [
    "ALLOWED_IMAGE_EXT",
    "ALLOWED_VIDEO_EXT",
    "delete_file",
    "is_configured",
    "upload_file",
]

_CONTENT_TYPES = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
}


@lru_cache
def _s3_client():
    settings = get_settings()
    kwargs: dict = {"region_name": (settings.AWS_S3_REGION or "ap-south-1").strip()}
    key_id = (settings.AWS_ACCESS_KEY_ID or "").strip()
    secret = (settings.AWS_SECRET_ACCESS_KEY or "").strip()
    if key_id and secret:
        kwargs["aws_access_key_id"] = key_id
        kwargs["aws_secret_access_key"] = secret
    return boto3.client("s3", **kwargs)


def is_configured() -> bool:
    settings = get_settings()
    return bool(
        (settings.AWS_S3_BUCKET or "").strip()
        and (settings.AWS_CLOUDFRONT_URL or "").strip()
    )


def _should_optimize(ext: str, allowed_ext: set[str]) -> bool:
    if allowed_ext & ALLOWED_VIDEO_EXT and ext in ALLOWED_VIDEO_EXT:
        return False
    return ext in ALLOWED_IMAGE_EXT or ext in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
    }


def _object_key(folder: str, ext: str) -> str:
    settings = get_settings()
    prefix = (settings.AWS_S3_PREFIX or "").strip().strip("/")
    key = build_key(folder, ext)
    return f"{prefix}/{key}" if prefix else key


def _cdn_url(key: str) -> str:
    base = get_settings().AWS_CLOUDFRONT_URL.rstrip("/")
    return f"{base}/{key.lstrip('/')}"


def _key_from_public_url(url: str) -> str:
    if not url:
        return ""
    settings = get_settings()
    cdn = (settings.AWS_CLOUDFRONT_URL or "").rstrip("/")
    if cdn and url.startswith(cdn):
        return url[len(cdn) :].lstrip("/").split("?", 1)[0]

    parsed = urlparse(url)
    path = (parsed.path or "").lstrip("/")
    if not path:
        return ""
    bucket = (settings.AWS_S3_BUCKET or "").strip()
    # Virtual-hosted–style: bucket.s3.region.amazonaws.com/key
    host = (parsed.netloc or "").lower()
    if bucket and host.startswith(f"{bucket.lower()}."):
        return path
    # Path-style or custom origin
    if path.startswith(f"{bucket}/"):
        return path[len(bucket) + 1 :]
    return path


async def upload_file(
    file: UploadFile,
    folder: str,
    *,
    allowed_ext: set[str] = ALLOWED_IMAGE_EXT,
    default_ext: str = ".jpg",
) -> str:
    settings = get_settings()
    if not is_configured():
        raise HTTPException(
            status_code=500,
            detail=(
                "S3 storage is not configured "
                "(set AWS_S3_BUCKET and AWS_CLOUDFRONT_URL, or STORAGE_BACKEND=local)"
            ),
        )

    ext = validate_ext(file.filename, allowed_ext, default_ext)
    content = await file.read()
    content_type = file.content_type or _CONTENT_TYPES.get(ext, "application/octet-stream")

    if _should_optimize(ext, allowed_ext):
        content, ext, content_type = optimize_image_bytes(content, source_ext=ext)

    key = _object_key(folder, ext)
    bucket = settings.AWS_S3_BUCKET.strip()

    def _put() -> None:
        client = _s3_client()
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )

    try:
        await asyncio.to_thread(_put)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "ClientError")
        raise HTTPException(
            status_code=502,
            detail=f"S3 upload failed ({code}): {exc}",
        ) from exc

    return _cdn_url(key)


async def delete_file(url: str) -> None:
    if not url or not is_configured():
        return

    key = _key_from_public_url(url)
    if not key:
        return

    bucket = get_settings().AWS_S3_BUCKET.strip()

    def _delete() -> None:
        client = _s3_client()
        try:
            client.delete_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey", "NotFound"):
                return
            logger.warning("S3 delete failed for %s: %s", key, exc)

    await asyncio.to_thread(_delete)