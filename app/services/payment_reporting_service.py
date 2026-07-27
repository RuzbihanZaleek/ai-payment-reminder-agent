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

        return {
            "total_payments_received": len(self.payment_service.get_all_payments()),
            "pending_approval_count": self.payment_service.count_pending_approvals(),
        }