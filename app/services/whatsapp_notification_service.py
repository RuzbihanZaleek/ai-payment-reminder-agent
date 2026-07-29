import time
from datetime import date
from decimal import Decimal

import httpx

from app.core.logger import get_logger
from app.services.notification_service import NotificationService
from app.services.retry_policy import RetryPolicy, RetryOutcome


logger = get_logger(__name__)


class WhatsAppNotificationService(NotificationService):
    """Sends WhatsApp messages with retry + exponential backoff.

    ``send(recipient, message) -> bool`` delivers a free-form text message (only
    valid inside the 24h customer-service window). ``send_template(...)`` and the
    ``send_payment_reminder_template(...)`` convenience wrapper deliver a
    pre-approved template, required for business-initiated (proactive) messages.

    All three share one delivery path: delivery failures always return ``False``
    (never propagated to the workflow); transient failures (timeout, connection
    error, HTTP 429/5xx) are retried, deterministic client errors (400/401/403)
    are not.
    """

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        api_version: str,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0,
        timeout_seconds: float = 10.0,
        reminder_template_name: str = "",
        reminder_template_language: str = "en_US",
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds
        self.reminder_template_name = reminder_template_name
        self.reminder_template_language = reminder_template_language
        self._retry_policy = RetryPolicy(
            max_retries=max_retries,
            base_delay_seconds=retry_delay_seconds,
        )

    def send(
        self,
        recipient: str,
        message: str,
    ) -> bool:

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message},
        }

        return self._deliver(recipient, payload)

    def send_template(
        self,
        recipient: str,
        template_name: str,
        language_code: str,
        body_parameters: list | None = None,
    ) -> bool:
        """Deliver a pre-approved WhatsApp template.

        ``body_parameters`` fills the ``{{1}}``, ``{{2}}`` ... placeholders in the
        template body, in order. Meta requires the template to be approved and
        the parameter count to match the template exactly.
        """

        template: dict = {
            "name": template_name,
            "language": {"code": language_code},
        }

        if body_parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(param)}
                        for param in body_parameters
                    ],
                }
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": template,
        }

        return self._deliver(recipient, payload)

    def send_payment_reminder_template(
        self,
        recipient: str,
        name: str,
        amount: Decimal,
        due_date: date,
    ) -> bool:
        """Clean abstraction for the daily payment reminder.

        Maps to the configured reminder template's body placeholders in order:
        ``{{1}}`` = customer name, ``{{2}}`` = amount, ``{{3}}`` = due date.
        """

        return self.send_template(
            recipient,
            self.reminder_template_name,
            self.reminder_template_language,
            body_parameters=[
                name,
                self._format_amount(amount),
                self._format_due_date(due_date),
            ],
        )

    def _deliver(self, recipient: str, payload: dict) -> bool:

        url = (
            f"https://graph.facebook.com/{self.api_version}"
            f"/{self.phone_number_id}/messages"
        )

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
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

    @staticmethod
    def _format_amount(amount: Decimal) -> str:

        # Whole amounts render without decimals ($20), otherwise keep cents
        # ($19.50). Mirrors the formatting used in the reminder text.
        if amount == amount.to_integral_value():
            return f"${amount:,.0f}"

        return f"${amount:,.2f}"

    @staticmethod
    def _format_due_date(due_date: date) -> str:

        return due_date.isoformat() if due_date is not None else "today"
