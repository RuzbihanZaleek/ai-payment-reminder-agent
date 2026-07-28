"""Executes a confirmed PendingAction by delegating to existing domain services.

Contains NO business logic of its own -- it maps an action type + payload onto
the right existing service call. All rules (validation, allocation, approval,
reminder policy, tenant ownership) stay inside those services.
"""

from datetime import date
from decimal import Decimal

from app.ai.actions.pending_action import ActionType
from app.schemas.contract import ContractCreate


class ActionExecutor:

    def __init__(
        self,
        contract_service,
        payment_approval_service,
        reminder_service,
        reminder_execution_service,
    ):
        self.contract_service = contract_service
        self.payment_approval_service = payment_approval_service
        self.reminder_service = reminder_service
        self.reminder_execution_service = reminder_execution_service

    def execute(self, pending_action) -> dict:
        action_type = pending_action.action_type
        payload = pending_action.payload_json or {}
        user_id = pending_action.user_id

        if action_type == ActionType.CREATE_CONTRACT.value:
            return self._create_contract(user_id, payload)
        if action_type == ActionType.APPROVE_PAYMENT.value:
            return self._approve_payment(user_id, payload)
        if action_type == ActionType.REJECT_PAYMENT.value:
            return self._reject_payment(user_id, payload)
        if action_type == ActionType.SEND_REMINDERS.value:
            return self._send_reminders(user_id)

        return {"success": False, "message": "This action is no longer supported."}

    def _create_contract(self, user_id: int, payload: dict) -> dict:
        # ContractCreate enforces the contract validation rules; ContractService
        # performs the write (with its own audit).
        contract_create = ContractCreate(
            reference_code=payload["reference_code"],
            name=payload["name"],
            total_amount=Decimal(str(payload["total_amount"])),
            daily_amount=Decimal(str(payload["daily_amount"])),
            start_date=date.today(),
            whatsapp_chat_id=payload["whatsapp_chat_id"],
        )

        contract = self.contract_service.create_contract(contract_create, user_id=user_id)
        return {
            "success": True,
            "message": f"Contract {contract.reference_code} created successfully.",
        }

    def _approve_payment(self, user_id: int, payload: dict) -> dict:
        payment = self.payment_approval_service.approve_payment(
            payment_id=payload["payment_id"],
            approved_by=payload.get("reviewed_by", "whatsapp-ai"),
            user_id=user_id,
        )
        if payment is None:
            return {"success": False, "message": "Payment not found or not eligible for approval."}

        return {"success": True, "message": f"Payment {payload['payment_id']} approved."}

    def _reject_payment(self, user_id: int, payload: dict) -> dict:
        payment = self.payment_approval_service.reject_payment(
            payment_id=payload["payment_id"],
            rejected_by=payload.get("reviewed_by", "whatsapp-ai"),
            user_id=user_id,
        )
        if payment is None:
            return {"success": False, "message": "Payment not found or not eligible for rejection."}

        return {"success": True, "message": f"Payment {payload['payment_id']} rejected."}

    def _send_reminders(self, user_id: int) -> dict:
        # Reuse the existing reminder policy (which contracts are due) and the
        # existing reminder workflow (how a reminder is executed), scoped to the
        # user's own contracts.
        due = self.reminder_service.get_pending_reminders()
        owned_ids = {c.id for c in self.contract_service.get_user_contracts(user_id)}

        sent = 0
        for contract in due:
            if contract.id in owned_ids:
                self.reminder_execution_service.execute(contract)
                sent += 1

        return {"success": True, "message": f"Sent {sent} reminder(s) for due contracts."}
