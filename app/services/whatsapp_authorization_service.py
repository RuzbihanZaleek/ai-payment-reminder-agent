"""WhatsApp channel authorization guard (V1 security model).

Authorization decisions for AI actions arriving over WhatsApp live HERE, not in
the webhook/router/assistant. For Version 1, WhatsApp is limited to payment
messages and read-only financial queries: every lender-side WRITE action is
denied, because a WhatsApp sender is not an authenticated user (identity is only
derived from contract ownership). Authenticated JWT channels are unaffected.

Denied attempts are audited (with a masked phone) so abuse is visible.
"""

from app.core.logger import get_logger
from app.core.phone import mask_phone
from app.ai.assistant.intent import AssistantIntent


logger = get_logger(__name__)

# Intents that would cause (or trigger) a lender-side write. Denied over WhatsApp.
_BLOCKED_WHATSAPP_INTENTS = {
    AssistantIntent.CREATE_CONTRACT,
    AssistantIntent.UPDATE_CONTRACT,
    AssistantIntent.DELETE_CONTRACT,
    AssistantIntent.APPROVE_PAYMENT,
    AssistantIntent.REJECT_PAYMENT,
    AssistantIntent.SEND_REMINDERS,
    # Confirming would execute a pending write -- also blocked over WhatsApp.
    AssistantIntent.CONFIRM_ACTION,
}

_REASON_WRITE_DISABLED = "WHATSAPP_WRITE_ACTION_DISABLED"
_REASON_UNKNOWN_ACTION = "WHATSAPP_UNKNOWN_ACTION"


class WhatsAppAuthorizationService:

    def __init__(self, audit_service=None):
        self.audit_service = audit_service

    def authorize(self, phone: str, intent) -> dict:
        """Return {"allowed": bool, "reason": str|None} for a WhatsApp intent."""

        if intent in _BLOCKED_WHATSAPP_INTENTS:
            self._record_block(phone, intent, _REASON_WRITE_DISABLED)
            return {"allowed": False, "reason": _REASON_WRITE_DISABLED}

        # Recognized read/cancel/unknown intents are allowed.
        if isinstance(intent, AssistantIntent):
            return {"allowed": True, "reason": None}

        # Anything that isn't a recognized intent is rejected (fail closed).
        self._record_block(phone, intent, _REASON_UNKNOWN_ACTION)
        return {"allowed": False, "reason": _REASON_UNKNOWN_ACTION}

    def _record_block(self, phone: str, intent, reason: str) -> None:
        masked = mask_phone(phone)
        attempted = getattr(intent, "value", str(intent))
        logger.info(
            "whatsapp_action_blocked",
            extra={"phone": masked, "attempted_intent": attempted, "reason": reason},
        )

        if self.audit_service is not None:
            self.audit_service.record(
                action=self.audit_service.WHATSAPP_ACTION_BLOCKED,
                user_id=None,
                entity_type="whatsapp",
                metadata={
                    "phone": masked,
                    "attempted_intent": attempted,
                    "reason": reason,
                },
            )
