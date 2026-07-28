"""Human-in-the-loop action orchestration.

Proposes write actions (creating a PENDING_CONFIRMATION row -- never executing),
and, only after the user confirms, executes them via the ActionExecutor (which
delegates to existing domain services). Owns lifecycle + tenant scoping + audit;
contains no business rules.
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pydantic import ValidationError

from app.core.logger import get_logger
from app.core.phone import is_valid_whatsapp_number, normalize_phone
from app.schemas.contract import ContractCreate
from app.models.pending_action import PendingAction
from app.ai.actions.pending_action import ActionType, PendingActionStatus
from app.ai.actions.action_executor import ActionExecutor
from app.core.metrics import (
    record_ai_action_created,
    record_ai_action_executed,
    record_ai_action_cancelled,
    record_ai_action_expired,
)


logger = get_logger(__name__)

_CONFIRM_HINT = "\n\nReply YES to confirm or NO to cancel."


class ActionService:

    def __init__(
        self,
        repository,
        executor: ActionExecutor,
        payment_approval_service,
        audit_service=None,
        timeout_minutes: int = 15,
    ):
        self.repository = repository
        self.executor = executor
        self.payment_approval_service = payment_approval_service
        self.audit_service = audit_service
        self.timeout_minutes = timeout_minutes

    # --- proposing ----------------------------------------------------------

    def propose(self, user_id: int, action_type: ActionType, params: dict) -> dict:
        """Validate + create a pending action. Returns {"message", "created"}."""

        if action_type == ActionType.CREATE_CONTRACT:
            return self._propose_create_contract(user_id, params)
        if action_type in (ActionType.APPROVE_PAYMENT, ActionType.REJECT_PAYMENT):
            return self._propose_payment_review(user_id, action_type, params)
        if action_type == ActionType.SEND_REMINDERS:
            action = self._create(user_id, action_type, {})
            return {
                "message": "I'm ready to send today's due reminders for your contracts."
                + _CONFIRM_HINT,
                "created": True,
                "action_id": action.id,
            }

        return {"message": "That action isn't supported.", "created": False}

    def _propose_create_contract(self, user_id: int, params: dict) -> dict:
        name = params.get("name")
        total = params.get("total_amount")
        daily = params.get("daily_amount")
        phone = params.get("whatsapp_chat_id")

        if not name or total is None or daily is None:
            return {
                "message": "To create a contract I need the customer name, total "
                "amount and daily amount.",
                "created": False,
            }

        # A real WhatsApp number is mandatory -- never a placeholder.
        if not phone or not is_valid_whatsapp_number(phone):
            return {
                "message": "I need a valid WhatsApp phone number for the customer "
                "before I can create this contract.",
                "created": False,
            }

        reference_code = f"AI-{uuid.uuid4().hex[:8].upper()}"
        whatsapp_chat_id = normalize_phone(phone)

        payload = {
            "name": name,
            "total_amount": str(total),
            "daily_amount": str(daily),
            "reference_code": reference_code,
            "whatsapp_chat_id": whatsapp_chat_id,
        }

        # Validate up-front using the existing schema (single source of rules).
        try:
            ContractCreate(
                reference_code=reference_code,
                name=name,
                total_amount=Decimal(str(total)),
                daily_amount=Decimal(str(daily)),
                start_date=datetime.now(timezone.utc).date(),
                whatsapp_chat_id=whatsapp_chat_id,
            )
        except ValidationError as exc:
            return {"message": f"I couldn't propose that contract: {self._first_error(exc)}.", "created": False}

        action = self._create(user_id, ActionType.CREATE_CONTRACT, payload)
        message = (
            "I'm ready to create this contract.\n\n"
            f"Customer:\n{name}\n\n"
            f"Total:\n{total}\n\n"
            f"Daily:\n{daily}\n\n"
            f"WhatsApp:\n{whatsapp_chat_id}"
            + _CONFIRM_HINT
        )
        return {"message": message, "created": True, "action_id": action.id}

    def _propose_payment_review(self, user_id: int, action_type: ActionType, params: dict) -> dict:
        verb = "approve" if action_type == ActionType.APPROVE_PAYMENT else "reject"

        pendings = self.payment_approval_service.get_pending_approvals(user_id)
        if not pendings:
            return {"message": "You have no payments awaiting approval.", "created": False}

        payment_id = params.get("payment_id")
        if payment_id is not None:
            target = next((p for p in pendings if p.id == payment_id), None)
            if target is None:
                return {"message": f"Payment #{payment_id} isn't awaiting your approval.", "created": False}
        elif len(pendings) == 1:
            target = pendings[0]
        else:
            listed = ", ".join(f"#{p.id} ({p.amount})" for p in pendings)
            return {
                "message": f"You have {len(pendings)} payments awaiting approval: {listed}. "
                f"Which one should I {verb}? (say '{verb} payment <id>')",
                "created": False,
            }

        payload = {"payment_id": target.id, "reviewed_by": "whatsapp-ai"}
        action = self._create(user_id, action_type, payload)
        message = (
            f"I'm ready to {verb} payment #{target.id} ({target.amount})." + _CONFIRM_HINT
        )
        return {"message": message, "created": True, "action_id": action.id}

    # --- confirming / cancelling / expiring ---------------------------------

    def get_latest_pending(self, user_id: int):
        return self.repository.get_latest_pending_for_user(user_id)

    def confirm_and_execute(self, user_id: int) -> dict:
        pending = self.get_latest_pending(user_id)
        if pending is None:
            return {"success": False, "message": "There's nothing to confirm."}

        self._audit("AI_ACTION_CONFIRMED", user_id, pending)

        start = time.perf_counter()
        try:
            result = self.executor.execute(pending)
        except Exception:
            logger.exception("ai_action_execution_failed", extra={"action_id": pending.id})
            return {"success": False, "message": "Something went wrong executing that action."}

        duration_ms = int((time.perf_counter() - start) * 1000)

        if result.get("success"):
            # Exactly-once: mark EXECUTED so it can never run again.
            self.repository.set_status(pending.id, PendingActionStatus.EXECUTED)
            record_ai_action_executed()
            self._audit("AI_ACTION_EXECUTED", user_id, pending, {"duration_ms": duration_ms})

        return {"success": result.get("success", False), "message": result["message"]}

    def cancel_latest(self, user_id: int) -> dict:
        pending = self.get_latest_pending(user_id)
        if pending is None:
            return {"success": False, "message": "There's nothing to cancel."}

        self.repository.set_status(pending.id, PendingActionStatus.CANCELLED)
        record_ai_action_cancelled()
        self._audit("AI_ACTION_CANCELLED", user_id, pending)
        return {"success": True, "message": "Action cancelled."}

    def expire_stale(self) -> int:
        expired = self.repository.get_expired()
        for action in expired:
            self.repository.set_status(action.id, PendingActionStatus.EXPIRED)
            self._audit("AI_ACTION_EXPIRED", action.user_id, action)

        record_ai_action_expired(len(expired))
        return len(expired)

    # --- helpers ------------------------------------------------------------

    def _create(self, user_id: int, action_type: ActionType, payload: dict) -> PendingAction:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.timeout_minutes)
        action = self.repository.create(
            PendingAction(
                user_id=user_id,
                action_type=action_type.value,
                payload_json=payload,
                status=PendingActionStatus.PENDING_CONFIRMATION.value,
                expires_at=expires_at,
            )
        )
        record_ai_action_created()
        self._audit("AI_ACTION_CREATED", user_id, action)
        return action

    def _audit(self, action_name: str, user_id: int, pending, extra: dict | None = None) -> None:
        if self.audit_service is None:
            return

        metadata = {"action_type": pending.action_type}
        if extra:
            metadata.update(extra)

        self.audit_service.record(
            action=getattr(self.audit_service, action_name),
            user_id=user_id,
            entity_type="pending_action",
            entity_id=pending.id,
            metadata=metadata,
        )

    @staticmethod
    def _first_error(exc: ValidationError) -> str:
        errors = exc.errors()
        if not errors:
            return "invalid input"
        return errors[0].get("msg", "invalid input")
