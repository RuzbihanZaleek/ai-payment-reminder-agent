from datetime import datetime, timezone

from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.contract_repository import ContractRepository


class PaymentApprovalService:

    def __init__(
        self,
        payment_repository: PaymentRepository,
        contract_repository: ContractRepository,
    ):
        self.payment_repository = payment_repository
        self.contract_repository = contract_repository

    def _is_owned_by(self, payment: Payment | None, user_id: int) -> bool:

        if payment is None:
            return False

        contract = self.contract_repository.get_by_id(payment.contract_id)

        return contract is not None and contract.user_id == user_id

    def get_pending_approvals(self, user_id: int) -> list[Payment]:

        pending = self.payment_repository.get_by_approval_status(
            ApprovalStatus.PENDING
        )

        return [p for p in pending if self._is_owned_by(p, user_id)]

    def approve_payment(
        self,
        payment_id: int,
        approved_by: str,
        user_id: int,
    ) -> Payment | None:

        payment = self.payment_repository.get_by_id(payment_id)

        if not self._is_owned_by(payment, user_id):
            return None

        payment.status = PaymentStatus.APPROVED
        payment.approval_status = ApprovalStatus.APPROVED
        payment.approved_by = approved_by
        payment.approved_at = datetime.now(timezone.utc)

        return self.payment_repository.update(payment)

    def reject_payment(
        self,
        payment_id: int,
        rejected_by: str,
        user_id: int,
    ) -> Payment | None:

        payment = self.payment_repository.get_by_id(payment_id)

        if not self._is_owned_by(payment, user_id):
            return None

        # Rejection is terminal: both the approval flag and the payment status
        # become REJECTED so the payment never affects the balance.
        payment.approval_status = ApprovalStatus.REJECTED
        payment.status = PaymentStatus.REJECTED

        return self.payment_repository.update(payment)
