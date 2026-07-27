from decimal import Decimal

from app.services.payment_reporting_service import PaymentReportingService


class PaymentAnalyticsService:

    def __init__(
        self,
        payment_reporting_service: PaymentReportingService,
    ):
        self.payment_reporting_service = payment_reporting_service

    def get_payment_analytics(self, user_id: int) -> dict:

        stats = self.payment_reporting_service.get_payment_stats(user_id)

        count = stats["payment_transaction_count"]
        received = stats["total_amount_received"]

        average = (received / count) if count else Decimal("0")

        return {
            "total_amount_received": received,
            "payment_transaction_count": count,
            "average_payment_amount": average,
            "pending_review_amount": stats["pending_review_amount"],
        }