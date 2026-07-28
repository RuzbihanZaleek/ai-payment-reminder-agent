"""Grounded financial recommendations (read-only).

Composes the other insight services (like a reporting composer) and turns their
factual outputs into short, data-backed recommendation strings. Every line is
derived from real figures -- it never produces speculative advice.
"""

from decimal import Decimal

from app.services.insights.financial_insight_service import FinancialInsightService
from app.services.insights.contract_insight_service import ContractInsightService
from app.services.insights.payment_insight_service import PaymentInsightService


_CONCENTRATION_THRESHOLD = Decimal("0.5")


class RecommendationService:

    def __init__(
        self,
        financial_insight_service: FinancialInsightService,
        contract_insight_service: ContractInsightService,
        payment_insight_service: PaymentInsightService,
    ):
        self.financial_insight_service = financial_insight_service
        self.contract_insight_service = contract_insight_service
        self.payment_insight_service = payment_insight_service

    def generate(self, user_id: int) -> list[str]:
        recommendations: list[str] = []

        summary = self.financial_insight_service.get_financial_summary(user_id)
        overdue = self.contract_insight_service.get_overdue_contracts(user_id)
        near_completion = self.contract_insight_service.get_contracts_near_completion(user_id)
        active = self.contract_insight_service.get_active_contracts(user_id)

        # Overdue.
        if not overdue:
            recommendations.append("No contracts appear overdue.")
        else:
            for contract in overdue[:3]:
                recommendations.append(
                    f"{contract['name']} appears behind on expected payments "
                    f"({contract['remaining_amount']} still outstanding). "
                    "Consider following up."
                )

        # Near completion.
        for contract in near_completion[:3]:
            recommendations.append(
                f"Contract {contract['reference_code']} is almost completed. "
                f"Only {contract['remaining_amount']} remains outstanding."
            )

        # Collection health.
        rate = summary["collection_rate"]
        if rate >= 0.9:
            recommendations.append(
                "Your collection rate exceeds 90%. Your portfolio is performing well."
            )
        elif rate < 0.5 and summary["total_expected_return"] > 0:
            recommendations.append(
                f"Your collection rate is {round(rate * 100, 1)}%. "
                "Consider following up on outstanding balances."
            )

        # Concentration risk.
        capital = summary["total_active_capital"]
        if capital > 0 and active:
            largest = max(active, key=lambda c: c["total_amount"])
            if largest["total_amount"] > capital * _CONCENTRATION_THRESHOLD and len(active) > 1:
                recommendations.append(
                    f"Most of your active capital is concentrated in one contract "
                    f"({largest['reference_code']}). Diversifying future investments "
                    "may reduce risk."
                )

        return recommendations
