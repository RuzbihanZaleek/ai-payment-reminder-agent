"""Contract-level insights (read-only).

Centralizes a per-contract analysis (paid / remaining / schedule adherence) once
and derives every listed view from it. All balance figures come from
PaymentService (APPROVED-only rules) -- no business rules are re-invented.

Definitions:
- near completion: 0 < remaining <= 10% of the contract total.
- overdue: an ACTIVE contract behind its expected schedule
  (paid < daily_amount * days_elapsed) with remaining > 0.
"""

from datetime import date
from decimal import Decimal

from app.models.contract import ContractStatus
from app.services.contract_service import ContractService
from app.services.payment_service import PaymentService


_NEAR_COMPLETION_THRESHOLD = Decimal("0.10")


def _ratio(numerator: Decimal, denominator: Decimal) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator / denominator), 4)


class ContractInsightService:

    def __init__(
        self,
        contract_service: ContractService,
        payment_service: PaymentService,
    ):
        self.contract_service = contract_service
        self.payment_service = payment_service

    # --- central analysis ---------------------------------------------------

    def _analyze(self, user_id: int) -> list[dict]:
        today = date.today()
        rows = []

        for contract in self.contract_service.get_user_contracts(user_id):
            total = contract.total_amount
            paid = self.payment_service.calculate_total_paid(contract.id)
            remaining = self.payment_service.calculate_remaining_amount(total, contract.id)

            status = (
                contract.status.value
                if hasattr(contract.status, "value")
                else contract.status
            )
            is_active = contract.status == ContractStatus.ACTIVE

            days_elapsed = max((today - contract.start_date).days, 0)
            expected_by_now = min(contract.daily_amount * days_elapsed, total)

            is_overdue = bool(is_active and remaining > 0 and paid < expected_by_now)
            is_near_completion = bool(
                remaining > 0 and total > 0
                and remaining <= total * _NEAR_COMPLETION_THRESHOLD
            )

            rows.append(
                {
                    "contract_id": contract.id,
                    "reference_code": contract.reference_code,
                    "name": contract.name,
                    "status": status,
                    "total_amount": total,
                    "total_paid": paid,
                    "remaining_amount": remaining,
                    "daily_amount": contract.daily_amount,
                    "completion_rate": _ratio(paid, total),
                    "expected_by_now": expected_by_now,
                    "performance_ratio": _ratio(paid, expected_by_now),
                    "is_overdue": is_overdue,
                    "is_near_completion": is_near_completion,
                    "updated_at": getattr(contract, "updated_at", None),
                    "_is_active": is_active,
                    "_is_completed": contract.status == ContractStatus.COMPLETED,
                }
            )

        return rows

    @staticmethod
    def _clean(rows: list[dict]) -> list[dict]:
        # Drop private keys before handing rows outward.
        return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]

    # --- summaries ----------------------------------------------------------

    def get_contract_summary(self, user_id: int) -> dict:
        rows = self._analyze(user_id)
        return {
            "total_contracts": len(rows),
            "active_contracts": sum(1 for r in rows if r["_is_active"]),
            "completed_contracts": sum(1 for r in rows if r["_is_completed"]),
            "near_completion": sum(1 for r in rows if r["is_near_completion"]),
            "overdue": sum(1 for r in rows if r["is_overdue"]),
        }

    def get_active_contracts(self, user_id: int) -> list[dict]:
        return self._clean([r for r in self._analyze(user_id) if r["_is_active"]])

    def get_completed_contracts(self, user_id: int) -> list[dict]:
        return self._clean([r for r in self._analyze(user_id) if r["_is_completed"]])

    def get_contract_completion_rate(self, user_id: int) -> float:
        rows = self._analyze(user_id)
        completed = sum(1 for r in rows if r["_is_completed"])
        return _ratio(Decimal(completed), Decimal(len(rows))) if rows else 0.0

    def get_contract_distribution(self, user_id: int) -> dict:
        distribution: dict[str, int] = {}
        for r in self._analyze(user_id):
            distribution[r["status"]] = distribution.get(r["status"], 0) + 1
        return distribution

    def get_contracts_near_completion(self, user_id: int) -> list[dict]:
        return self._clean(
            [r for r in self._analyze(user_id) if r["is_near_completion"]]
        )

    def get_recently_completed_contracts(self, user_id: int, limit: int = 5) -> list[dict]:
        completed = [r for r in self._analyze(user_id) if r["_is_completed"]]
        completed.sort(key=lambda r: r["updated_at"] or date.min, reverse=True)
        return self._clean(completed[:limit])

    def get_overdue_contracts(self, user_id: int) -> list[dict]:
        return self._clean([r for r in self._analyze(user_id) if r["is_overdue"]])

    def get_highest_balance_contracts(self, user_id: int, limit: int = 5) -> list[dict]:
        rows = [r for r in self._analyze(user_id) if r["remaining_amount"] > 0]
        rows.sort(key=lambda r: r["remaining_amount"], reverse=True)
        return self._clean(rows[:limit])

    def get_lowest_balance_contracts(self, user_id: int, limit: int = 5) -> list[dict]:
        rows = [r for r in self._analyze(user_id) if r["remaining_amount"] > 0]
        rows.sort(key=lambda r: r["remaining_amount"])
        return self._clean(rows[:limit])

    def get_best_performing_contracts(self, user_id: int, limit: int = 5) -> list[dict]:
        rows = [r for r in self._analyze(user_id) if r["_is_active"]]
        rows.sort(key=lambda r: r["performance_ratio"], reverse=True)
        return self._clean(rows[:limit])

    def get_worst_performing_contracts(self, user_id: int, limit: int = 5) -> list[dict]:
        rows = [r for r in self._analyze(user_id) if r["_is_active"]]
        rows.sort(key=lambda r: r["performance_ratio"])
        return self._clean(rows[:limit])
