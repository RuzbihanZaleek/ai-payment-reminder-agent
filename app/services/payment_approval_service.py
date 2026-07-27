from datetime import datetime, timezone

from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.repositories.payment_repository import PaymentRepository


class PaymentApprovalService:

    def __init__(
        self,
        payment_repository: PaymentRepository,
    ):
        self.payment_repository = payment_repository

    def get_pending_approvals(self) -> list[Payment]:

        return self.payment_repository.get_by_approval_status(
            ApprovalStatus.PENDING
        )

    def approve_payment(
        self,
        payment_id: int,
        approved_by: str,
    ) -> Payment | None:

        payment = self.payment_repository.get_by_id(payment_id)

        if payment is None:
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
    ) -> Payment | None:

        payment = self.payment_repository.get_by_id(payment_id)

        if payment is None:
            return None

        # Rejection is terminal: both the approval flag and the payment status
        # become REJECTED so the payment never affects the balance.
        payment.approval_status = ApprovalStatus.REJECTED
        payment.status = PaymentStatus.REJECTED

        return self.payment_repository.update(payment)
