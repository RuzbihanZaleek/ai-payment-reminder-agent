from app.models.contract import Contract, ContractStatus
from app.services.contract_service import ContractService
from app.services.payment_service import PaymentService


class ReminderService:

    def __init__(
        self,
        contract_service: ContractService,
        payment_service: PaymentService,
    ):
        self.contract_service = contract_service
        self.payment_service = payment_service

    def get_pending_reminders(self) -> list[Contract]:

        pending = []

        for contract in self.contract_service.get_all_contracts():

            if not self._is_due(contract):
                continue

            remaining = self.payment_service.calculate_remaining_amount(
                contract.total_amount,
                contract.id,
            )

            if remaining > 0:
                pending.append(contract)

        return pending

    def _is_due(self, contract: Contract) -> bool:

        # A reminder is only due for active contracts; completed / paused /
        # cancelled contracts are skipped.
        return contract.status == ContractStatus.ACTIVE
