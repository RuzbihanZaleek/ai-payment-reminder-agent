from app.services.payment_service import PaymentService
from app.repositories.filters import PaymentFilter
from app.repositories.pagination import PageResult
from app.enums.sort_order import SortOrder


class PaymentReportingService:

    def __init__(
        self,
        payment_service: PaymentService,
    ):
        self.payment_service = payment_service

    def get_payment_history(
        self,
        contract_id: int,
        payment_filter: PaymentFilter,
        page: int,
        page_size: int,
        order: SortOrder,
    ) -> PageResult:

        return self.payment_service.get_contract_payments_page(
            contract_id,
            payment_filter,
            page,
            page_size,
            order,
        )

    def get_payment_stats(self, user_id: int) -> dict:

        payments = self.payment_service.get_user_payments(user_id)

        return {
            "payment_transaction_count": len(payments),
            # Confirmed money only (approval_status == APPROVED).
            "total_amount_received": self.payment_service.calculate_total_received_for_user(user_id),
            # Payments awaiting a human decision (manual review + PENDING).
            "pending_review_count": self.payment_service.count_pending_reviews_for_user(user_id),
            "pending_review_amount": self.payment_service.calculate_pending_review_amount_for_user(user_id),
        }