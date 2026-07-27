from decimal import Decimal

from app.models.payment_receipt import PaymentReceipt
from app.repositories.payment_receipt_repository import PaymentReceiptRepository
from app.services.contract_service import ContractService
from app.services.payment_service import PaymentService
from app.services.payment_allocation_formatter import PaymentAllocationFormatter


class PaymentReceiptService:
    """Builds and persists an audit snapshot per created payment."""

    def __init__(
        self,
        payment_receipt_repository: PaymentReceiptRepository,
        contract_service: ContractService,
        payment_service: PaymentService,
        payment_allocation_formatter: PaymentAllocationFormatter,
    ):
        self.payment_receipt_repository = payment_receipt_repository
        self.contract_service = contract_service
        self.payment_service = payment_service
        self.payment_allocation_formatter = payment_allocation_formatter

    def generate_receipts(
        self,
        agent_run_id: int,
        payment_allocations: list,
    ) -> list:
        """Persist a PaymentReceipt per allocation and return lightweight dicts."""

        allocation_summary = self.payment_allocation_formatter.format(
            payment_allocations
        )

        receipts = []

        for allocation in payment_allocations:
            contract_id = allocation["contract_id"]
            amount = allocation["amount"]
            payment_id = allocation.get("payment_id")

            contract = self.contract_service.get_contract(contract_id)

            reference_code = allocation.get("reference_code")
            if reference_code is None and contract is not None:
                reference_code = contract.reference_code

            # The payment is already confirmed (APPROVED) by the time the
            # receipt runs, so the remaining amount reflects it -> that is the
            # "new" balance; adding the amount back reconstructs the "previous".
            if contract is not None:
                new_balance = self.payment_service.calculate_remaining_amount(
                    contract.total_amount,
                    contract_id,
                )
            else:
                new_balance = Decimal("0")

            previous_balance = new_balance + amount

            self.payment_receipt_repository.create(
                PaymentReceipt(
                    agent_run_id=agent_run_id,
                    contract_id=contract_id,
                    payment_id=payment_id,
                    amount=amount,
                    previous_balance=previous_balance,
                    new_balance=new_balance,
                    allocation_summary=allocation_summary,
                )
            )

            receipts.append(
                {
                    "contract_id": contract_id,
                    "reference_code": reference_code,
                    "amount": amount,
                    "previous_balance": previous_balance,
                    "new_balance": new_balance,
                }
            )

        return receipts