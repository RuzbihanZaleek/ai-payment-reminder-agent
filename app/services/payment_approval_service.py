from datetime import datetime, timezone

from app.core.logger import get_logger
from app.core.metrics import record_approval_request
from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.contract_repository import ContractRepository


logger = get_logger(__name__)


class PaymentApprovalService:

    def __init__(
        self,
        payment_repository: PaymentRepository,
        contract_repository: ContractRepository,
        audit_service=None,
    ):
        self.payment_repository = payment_repository
        self.contract_repository = contract_repository
        self.audit_service = audit_service

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

    def get_approvals_page(
        self,
        user_id: int,
        approval_status: ApprovalStatus,
        page: int,
        page_size: int,
        order,
    ):
        # Ownership scoping + pagination happen in a single DB query (join on the
        # owning contract), so the count and page are consistent.
        return self.payment_repository.get_by_approval_status_for_user_page(
            user_id,
            approval_status,
            page,
            page_size,
            order,
        )

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

        logger.info(
            "payment_approved",
            extra={
                "payment_id": payment_id,
                "user_id": user_id,
                "reviewed_by": approved_by,
            },
        )
        record_approval_request()

        if self.audit_service is not None:
            self.audit_service.record(
                action=self.audit_service.PAYMENT_APPROVED,
                user_id=user_id,
                entity_type="payment",
                entity_id=payment_id,
                metadata={"reviewed_by": approved_by},
            )

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

        logger.info(
            "payment_rejected",
            extra={
                "payment_id": payment_id,
                "user_id": user_id,
                "reviewed_by": rejected_by,
            },
        )
        record_approval_request()

        if self.audit_service is not None:
            self.audit_service.record(
                action=self.audit_service.PAYMENT_REJECTED,
                user_id=user_id,
                entity_type="payment",
                entity_id=payment_id,
                metadata={"reviewed_by": rejected_by},
            )

        return self.payment_repository.update(payment)
