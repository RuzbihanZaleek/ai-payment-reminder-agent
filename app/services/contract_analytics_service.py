from app.services.contract_reporting_service import ContractReportingService


class ContractAnalyticsService:

    def __init__(
        self,
        contract_reporting_service: ContractReportingService,
    ):
        self.contract_reporting_service = contract_reporting_service

    def get_contract_analytics(self, user_id: int) -> dict:

        stats = self.contract_reporting_service.get_contract_stats(user_id)

        total_value = stats["total_contract_value"]
        outstanding = stats["total_remaining_amount"]
        collected = total_value - outstanding

        collection_rate = (
            float(collected / total_value) if total_value else 0.0
        )

        return {
            "total_contract_value": total_value,
            "total_collected_amount": collected,
            "total_outstanding_amount": outstanding,
            "collection_rate": round(collection_rate, 4),
        }