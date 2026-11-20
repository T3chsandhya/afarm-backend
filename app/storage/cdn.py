"""Public CDN base URL for absolute media links (feeds, etc.)."""

from app.config import get_settings


def public_cdn_base() -> str:
    settings = get_settings()
    for value in (settings.AWS_CLOUDFRONT_URL, settings.BUNNY_CDN_URL):
        base = (value or "").strip().rstrip("/")
        if base:
            return base
    return ""