from decimal import Decimal

from app.models.contract import ContractStatus
from app.services.contract_service import ContractService
from app.services.payment_service import PaymentService


class ContractReportingService:

    def __init__(
        self,
        contract_service: ContractService,
        payment_service: PaymentService,
    ):
        self.contract_service = contract_service
        self.payment_service = payment_service

    def get_contract_summary(self, contract_id: int) -> dict | None:

        contract = self.contract_service.get_contract(contract_id)

        if contract is None:
            return None

        payments = self.payment_service.get_contract_payments(contract_id)

        return {
            "contract_id": contract.id,
            "reference_code": contract.reference_code,
            "name": contract.name,
            "total_amount": contract.total_amount,
            "total_paid": self.payment_service.calculate_total_paid(contract_id),
            "remaining_amount": self.payment_service.calculate_remaining_amount(
                contract.total_amount,
                contract_id,
            ),
            "payment_count": len(payments),
        }

    def get_contract_stats(self) -> dict:

        contracts = self.contract_service.get_all_contracts()

        total_remaining_amount = sum(
            (
                self.payment_service.calculate_remaining_amount(
                    contract.total_amount,
                    contract.id,
                )
                for contract in contracts
            ),
            Decimal("0"),
        )

        return {
            "total_contracts": len(contracts),
            "active_contracts": sum(
                1 for c in contracts if c.status == ContractStatus.ACTIVE
            ),
            "completed_contracts": sum(
                1 for c in contracts if c.status == ContractStatus.COMPLETED
            ),
            "total_remaining_amount": total_remaining_amount,
        }