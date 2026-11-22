import logging

from app.sms import exotel

logger = logging.getLogger("sms")


async def send_otp_sms(phone: str, otp: str, name: str = "") -> dict:
    """Send login OTP via Exotel (DLT template)."""
    if not exotel.is_configured():
        logger.error("Exotel SMS is not configured")
        raise RuntimeError("SMS service is not configured")

    return await exotel.send_otp_sms(phone, otp, name=name)