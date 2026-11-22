"""Exotel SMS (India, DLT) — login OTP."""

from __future__ import annotations

import logging
from typing import Any, Optional
import httpx

from app.config import settings

logger = logging.getLogger("sms.exotel")


def is_configured() -> bool:
    return bool(
        (settings.EXOTEL_ACCOUNT_SID or "").strip()
        and (settings.EXOTEL_API_KEY or "").strip()
        and (settings.EXOTEL_API_TOKEN or "").strip()
        and (settings.EXOTEL_SMS_SENDER or "").strip()
        and (settings.EXOTEL_DLT_ENTITY_ID or "").strip()
        and (settings.EXOTEL_DLT_TEMPLATE_ID or "").strip()
    )


def _api_base() -> str:
    host = (settings.EXOTEL_API_HOST or "api.exotel.com").strip()
    host = host.replace("https://", "").replace("http://", "").strip("/")
    return f"https://{host}"


def build_otp_body(otp: str, name: str = "") -> str:
    """Body must match the DLT-approved template (only {name}/{otp} vary)."""
    display_name = (name or "").strip() or "Customer"
    template = (settings.EXOTEL_OTP_BODY_TEMPLATE or "").strip()
    if not template:
        template = (
            "Hi {name}, your OTP is {otp} for Khulega Online by "
            "Sandhya Technology Solutions and Operations. It is valid for 10 minutes. "
            "Please do not share this OTP with anyone."
        )
    return template.format(name=display_name, otp=str(otp))


_SMS_OK_STATUS = frozenset({"queued", "sending", "sent", "delivered", "submitted"})
_SMS_FAIL_STATUS = frozenset({"failed", "rejected", "undelivered", "expired"})


def exotel_failure_message(data: Any) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    rest = data.get("RestException")
    if isinstance(rest, dict):
        msg = rest.get("Message") or rest.get("message")
        if msg:
            return str(msg)
    sms = data.get("SMSMessage")
    if not isinstance(sms, dict):
        return None

    status = (sms.get("Status") or "").strip().lower()
    if status in _SMS_OK_STATUS:
        # Accepted by Exotel — DetailedStatus may stay PENDING_TO_OPERATOR while delivering.
        return None
    if status in _SMS_FAIL_STATUS:
        return (sms.get("DetailedStatus") or sms.get("Status") or "SMS failed").strip()

    detailed = (sms.get("DetailedStatus") or "").strip()
    if detailed and detailed.lower() not in _SMS_OK_STATUS:
        return detailed
    return None


async def send_sms(to_phone_10: str, body: str) -> dict:
    if not is_configured():
        raise RuntimeError("Exotel SMS is not configured")

    sid = settings.EXOTEL_ACCOUNT_SID.strip()
    url = f"{_api_base()}/v1/Accounts/{sid}/Sms/send.json"
    to_e164 = f"+91{to_phone_10}" if len(to_phone_10) == 10 else to_phone_10

    form = {
        "From": settings.EXOTEL_SMS_SENDER.strip(),
        "To": to_e164,
        "Body": body,
        "DltEntityId": settings.EXOTEL_DLT_ENTITY_ID.strip(),
        "DltTemplateId": settings.EXOTEL_DLT_TEMPLATE_ID.strip(),
        "SmsType": (settings.EXOTEL_SMS_TYPE or "transactional").strip(),
        "Priority": "high",
        "EncodingType": "plain",
    }

    auth = (settings.EXOTEL_API_KEY.strip(), settings.EXOTEL_API_TOKEN.strip())

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, data=form, auth=auth)

    text = (resp.text or "").strip()
    if resp.status_code >= 400:
        logger.error("Exotel SMS HTTP %s: %s", resp.status_code, text[:500])
        raise RuntimeError(f"Exotel SMS failed (HTTP {resp.status_code})")

    try:
        data = resp.json()
    except Exception:
        data = {"raw": text}

    fail = exotel_failure_message(data)
    if fail:
        logger.error("Exotel SMS rejected: %s | body=%s", fail, data)
        raise RuntimeError(fail)

    logger.info("Exotel SMS queued to %s", to_phone_10[-4:].rjust(10, "*"))
    return data if isinstance(data, dict) else {"raw": data}


async def send_otp_sms(phone_10: str, otp: str, name: str = "") -> dict:
    body = build_otp_body(otp, name)
    return await send_sms(phone_10, body)