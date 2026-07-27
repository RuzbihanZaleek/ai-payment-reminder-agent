from app.models.payment import Payment
from app.services.payment_service import PaymentService


class PaymentReportingService:

    def __init__(
        self,
        payment_service: PaymentService,
    ):
        self.payment_service = payment_service

    def get_payment_history(self, contract_id: int) -> list[Payment]:

        return self.payment_service.get_contract_payments(contract_id)

    def get_payment_stats(self) -> dict:

        payments = self.payment_service.get_all_payments()

        return {
            "payment_transaction_count": len(payments),
            # Confirmed money only (approval_status == APPROVED).
            "total_amount_received": self.payment_service.calculate_total_received(),
            # Payments awaiting a human decision (manual review + PENDING).
            "pending_review_count": self.payment_service.count_pending_approvals(),
            "pending_review_amount": self.payment_service.calculate_pending_review_amount(),
        }