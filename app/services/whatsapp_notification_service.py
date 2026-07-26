import logging

import httpx

from app.services.notification_service import NotificationService


logger = logging.getLogger(__name__)


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

        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=10.0,
            )
        except Exception:
            # Delivery failures must never propagate to the workflow.
            logger.exception(
                "WhatsApp send request failed for recipient %s",
                recipient,
            )
            return False

        if 200 <= response.status_code < 300:
            return True

        logger.warning(
            "WhatsApp send returned %s for recipient %s: %s",
            response.status_code,
            recipient,
            response.text,
        )
        return False
