"""Proactive financial analysis (read-only).

Detects meaningful financial situations WITHOUT the user asking, purely by
reusing the existing insight services -- it re-implements no calculations. It
turns their factual outputs into risk signals, positives and a short summary
the advisor can surface proactively.
"""

from app.services.insights.financial_insight_service import FinancialInsightService
from app.services.insights.contract_insight_service import ContractInsightService
from app.services.insights.payment_insight_service import PaymentInsightService


# Below this collection rate (with real capital at work), performance is "low".
_LOW_COLLECTION_RATE = 0.3
# Below this consistency score, the payment pattern is "inconsistent".
_LOW_CONSISTENCY = 0.3


class ProactiveFinancialService:

    def __init__(
        self,
        financial_insight_service: FinancialInsightService,
        contract_insight_service: ContractInsightService,
        payment_insight_service: PaymentInsightService,
    ):
        self.financial_insight_service = financial_insight_service
        self.contract_insight_service = contract_insight_service
        self.payment_insight_service = payment_insight_service

    def analyze(self, user_id: int) -> dict:
        summary = self.financial_insight_service.get_financial_summary(user_id)
        overdue = self.contract_insight_service.get_overdue_contracts(user_id)
        near_completion = self.contract_insight_service.get_contracts_near_completion(user_id)
        completed = self.contract_insight_service.get_completed_contracts(user_id)
        consistency = self.payment_insight_service.get_payment_consistency(user_id)

        risks: list[str] = []
        positives: list[str] = []
        signals: list[dict] = []

        # Overdue contracts.
        if overdue:
            risks.append(f"{len(overdue)} contract(s) behind payment schedule")
            for contract in overdue[:5]:
                signals.append(
                    {
                        "type": "OVERDUE",
                        "contract_id": contract["contract_id"],
                        "reference_code": contract["reference_code"],
                        "message": f"{contract['name']} is behind payment schedule",
                    }
                )

        # Low collection performance.
        rate = summary["collection_rate"]
        if summary["total_expected_return"] > 0 and rate < _LOW_COLLECTION_RATE:
            risks.append(f"Collection performance is low ({round(rate * 100, 1)}%)")
            signals.append({"type": "LOW_COLLECTION", "message": "Collection performance is low"})

        # Payment inconsistency.
        if consistency["span_days"] > 0 and consistency["consistency_score"] < _LOW_CONSISTENCY:
            risks.append("Payment pattern is inconsistent")
            signals.append({"type": "INCONSISTENT_PAYMENTS", "message": "Payment pattern is inconsistent"})

        # Positives.
        if completed:
            positives.append(f"{len(completed)} contract(s) completed")
        for contract in near_completion[:5]:
            positives.append(
                f"Contract {contract['reference_code']} is close to completion "
                f"({contract['remaining_amount']} remaining)"
            )
            signals.append(
                {
                    "type": "NEAR_COMPLETION",
                    "contract_id": contract["contract_id"],
                    "reference_code": contract["reference_code"],
                    "message": "Contract is close to completion",
                }
            )
        if summary["total_expected_return"] > 0 and rate >= 0.9:
            positives.append("Strong collection rate (90%+)")

        return {
            "financial_health": summary,
            "summary": self._summarize(summary, risks),
            "risks": risks,
            "positives": positives,
            "signals": signals,
        }

    @staticmethod
    def _summarize(summary: dict, risks: list[str]) -> str:
        rate_pct = round(summary["collection_rate"] * 100, 1)
        if not summary["total_contracts"]:
            return "You don't have any contracts yet."
        if not risks:
            return (
                f"Your portfolio looks healthy: collection rate {rate_pct}% "
                f"with {summary['total_outstanding']} outstanding."
            )
        return (
            f"Collection rate {rate_pct}% with {len(risks)} item(s) needing "
            "attention."
        )
