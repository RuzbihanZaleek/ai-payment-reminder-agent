import time

import httpx

from app.core.logger import get_logger
from app.services.notification_service import NotificationService


logger = get_logger(__name__)


class WhatsAppNotificationService(NotificationService):

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        api_version: str,
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = api_version

    def send(
        self,
        recipient: str,
        message: str,
    ) -> bool:

        url = (
            f"https://graph.facebook.com/{self.api_version}"
            f"/{self.phone_number_id}/messages"
        )

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {
                "body": message,
            },
        }

        start = time.perf_counter()

        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)

            # Delivery failures must never propagate to the workflow.
            logger.warning(
                "whatsapp_message_failed",
                extra={
                    "recipient": recipient,
                    "status_code": None,
                    "duration_ms": duration_ms,
                    "error": str(exc),
                },
            )
            return False

        duration_ms = int((time.perf_counter() - start) * 1000)

        if 200 <= response.status_code < 300:
            logger.info(
                "whatsapp_message_sent",
                extra={
                    "recipient": recipient,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return True

        logger.warning(
            "whatsapp_message_failed",
            extra={
                "recipient": recipient,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return False
