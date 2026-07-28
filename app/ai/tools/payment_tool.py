"""Read-only payment tool for the assistant.

Delegates to PaymentService; enforces tenant ownership via ContractService
before returning any contract-scoped payment data.
"""

from decimal import Decimal

from app.services.payment_service import PaymentService
from app.services.contract_service import ContractService
from app.ai.tools.ownership import owned_contract


class PaymentTool:

    def __init__(
        self,
        payment_service: PaymentService,
        contract_service: ContractService,
    ):
        self.payment_service = payment_service
        self.contract_service = contract_service

    def get_payment_history(self, contract_id: int, user_id: int) -> list[dict]:
        if owned_contract(self.contract_service, contract_id, user_id) is None:
            return []

        payments = self.payment_service.get_contract_payments(contract_id)

        return [
            {
                "payment_id": p.id,
                "amount": p.amount,
                "payment_date": p.payment_date,
                "status": p.status.value if hasattr(p.status, "value") else p.status,
                "approval_status": (
                    p.approval_status.value
                    if hasattr(p.approval_status, "value")
                    else p.approval_status
                ),
            }
            for p in payments
        ]

    def get_total_paid(self, contract_id: int, user_id: int) -> Decimal | None:
        if owned_contract(self.contract_service, contract_id, user_id) is None:
            return None

        return self.payment_service.calculate_total_paid(contract_id)
