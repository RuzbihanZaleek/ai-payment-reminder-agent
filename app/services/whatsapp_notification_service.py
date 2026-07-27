import time

import httpx

from app.core.logger import get_logger
from app.services.notification_service import NotificationService
from app.services.retry_policy import RetryPolicy, RetryOutcome


logger = get_logger(__name__)


class WhatsAppNotificationService(NotificationService):
    """Sends WhatsApp messages with retry + exponential backoff.

    The public interface is unchanged: ``send(recipient, message) -> bool`` and
    delivery failures always return ``False`` (they never propagate to the
    workflow). Transient failures (timeout, connection error, HTTP 429/5xx) are
    retried; deterministic client errors (400/401/403) are not.
    """

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        api_version: str,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0,
        timeout_seconds: float = 10.0,
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds
        self._retry_policy = RetryPolicy(
            max_retries=max_retries,
            base_delay_seconds=retry_delay_seconds,
        )

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
            "text": {"body": message},
        }

        def _attempt() -> RetryOutcome:
            start = time.perf_counter()

            try:
                response = httpx.post(
                    url, headers=headers, json=payload, timeout=self.timeout_seconds
                )
            except Exception as exc:
                logger.warning(
                    "whatsapp_message_failed",
                    extra={
                        "recipient": recipient,
                        "status_code": None,
                        "duration_ms": int((time.perf_counter() - start) * 1000),
                        "error": str(exc),
                    },
                )
                return RetryOutcome(succeeded=False, transport_error=True)

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
                return RetryOutcome(succeeded=True, status_code=response.status_code)

            logger.warning(
                "whatsapp_message_failed",
                extra={
                    "recipient": recipient,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return RetryOutcome(succeeded=False, status_code=response.status_code)

        def _on_retry(attempt: int, outcome: RetryOutcome) -> None:
            logger.info(
                "whatsapp_retry_attempt",
                extra={
                    "attempt": attempt,
                    "status_code": outcome.status_code,
                    "recipient": recipient,
                    "backoff_seconds": self._retry_policy.backoff_seconds(attempt),
                },
            )

        outcome = self._retry_policy.run(_attempt, on_retry=_on_retry)

        return outcome.succeeded
