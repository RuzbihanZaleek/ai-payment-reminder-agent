"""Read-only assistant tools for financial insights.

Each tool delegates to exactly ONE insight service and performs NO calculations
of its own and NEVER touches repositories. They assemble a small bundle of the
relevant insight-service outputs for the LLM to phrase an answer from.

All financial figures are already tenant-scoped by ``user_id`` inside the
insight services (which in turn reuse the tenant-scoped domain services).
"""


class FinancialInsightTool:

    def __init__(self, financial_insight_service):
        self.service = financial_insight_service

    def get_financial_overview(self, user_id: int) -> dict:
        return {
            "summary": self.service.get_financial_summary(user_id),
            "roi": self.service.get_roi_summary(user_id),
            "cashflow": self.service.get_cashflow_summary(user_id),
        }


class ContractInsightTool:

    def __init__(self, contract_insight_service):
        self.service = contract_insight_service

    def get_contract_overview(self, user_id: int) -> dict:
        return {
            "summary": self.service.get_contract_summary(user_id),
            "distribution": self.service.get_contract_distribution(user_id),
            "near_completion": self.service.get_contracts_near_completion(user_id),
            "overdue": self.service.get_overdue_contracts(user_id),
            "highest_balance": self.service.get_highest_balance_contracts(user_id),
            "best_performing": self.service.get_best_performing_contracts(user_id),
            "worst_performing": self.service.get_worst_performing_contracts(user_id),
        }

    def get_overdue(self, user_id: int) -> dict:
        return {"overdue": self.service.get_overdue_contracts(user_id)}


class PaymentInsightTool:

    def __init__(self, payment_insight_service):
        self.service = payment_insight_service

    def get_payment_overview(self, user_id: int) -> dict:
        return {
            "summary": self.service.get_payment_summary(user_id),
            "consistency": self.service.get_payment_consistency(user_id),
            "streak": self.service.get_payment_streak(user_id),
            "recent_activity": self.service.get_recent_payment_activity(user_id),
        }

    def get_payment_trends(self, user_id: int) -> dict:
        return {
            "trends": self.service.get_payment_trends(user_id),
            "frequency": self.service.get_payment_frequency(user_id),
            "average_monthly": self.service.get_average_monthly_payment(user_id),
        }

    def get_payers(self, user_id: int) -> dict:
        return {
            "top_payers": self.service.get_top_payers(user_id),
            "fastest_payers": self.service.get_fastest_payers(user_id),
            "slowest_payers": self.service.get_slowest_payers(user_id),
        }


class SchedulerInsightTool:

    def __init__(self, scheduler_insight_service):
        self.service = scheduler_insight_service

    def get_reminder_overview(self, user_id: int | None = None) -> dict:
        # Scheduler data is system-level; user_id is accepted for a uniform
        # tool signature but not used to scope global reminder statistics.
        return {
            "statistics": self.service.get_reminder_statistics(),
            "recent_activity": self.service.get_recent_activity(),
            "recent_failures": self.service.get_recent_failures(),
        }


class RecommendationTool:

    def __init__(self, recommendation_service):
        self.service = recommendation_service

    def get_recommendations(self, user_id: int) -> dict:
        return {"recommendations": self.service.generate(user_id)}
