"""Media storage: local (default), bunny, or s3 + CloudFront."""

from fastapi import UploadFile

from app.config import get_settings
from app.storage import bunny, local, s3
from app.storage.base import ALLOWED_IMAGE_EXT, ALLOWED_VIDEO_EXT

__all__ = [
    "ALLOWED_IMAGE_EXT",
    "ALLOWED_VIDEO_EXT",
    "active_backend_name",
    "delete_file",
    "upload_file",
]


def active_backend_name(
    *,
    bunny_configured: bool | None = None,
    s3_configured: bool | None = None,
) -> str:
    preference = (get_settings().STORAGE_BACKEND or "local").strip().lower()
    if preference == "bunny":
        if bunny_configured is None:
            bunny_configured = bunny.is_configured()
        return "bunny" if bunny_configured else "local"
    if preference == "s3":
        if s3_configured is None:
            s3_configured = s3.is_configured()
        return "s3" if s3_configured else "local"
    return "local"


def _backend():
    name = active_backend_name()
    if name == "bunny":
        return bunny
    if name == "s3":
        return s3
    return local


async def upload_file(
    file: UploadFile,
    folder: str,
    *,
    allowed_ext: set[str] = ALLOWED_IMAGE_EXT,
    default_ext: str = ".jpg",
) -> str:
    return await _backend().upload_file(
        file,
        folder,
        allowed_ext=allowed_ext,
        default_ext=default_ext,
    )


async def delete_file(url: str) -> None:
    await _backend().delete_file(url)
