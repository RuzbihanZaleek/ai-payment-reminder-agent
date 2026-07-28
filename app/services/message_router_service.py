"""Routes an inbound WhatsApp message to the payment workflow or the AI assistant.

Reuses the EXISTING payment detector (PaymentMessageAgent) -- the very same
detector the payment workflow uses -- so there is no duplicated detection logic.
It only classifies; it never processes the message itself.
"""

from app.core.logger import get_logger
from app.enums.payment_detection import PaymentIntent


logger = get_logger(__name__)


class MessageRouterService:

    def __init__(self, payment_message_agent):
        self.payment_message_agent = payment_message_agent

    def is_payment(self, message: str, history: list | None = None) -> bool:
        """True if the message looks like a payment (→ payment workflow)."""

        detection = self.payment_message_agent.analyze_message(message, history)
        is_payment = detection.intent == PaymentIntent.PAYMENT_RECEIVED

        logger.info(
            "whatsapp_message_routed",
            extra={"route": "payment" if is_payment else "assistant"},
        )
        return is_payment
