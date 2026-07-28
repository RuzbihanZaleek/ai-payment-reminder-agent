"""Portfolio-level financial insights (read-only).

Owns the portfolio aggregation math. It reuses existing services for every rule
it can:

- "collected" / "outstanding" / contract totals come from
  ``ContractReportingService.get_contract_stats`` (which uses PaymentService's
  APPROVED-only balance rules) -- never re-implemented here.
- forward-looking income is derived from active contracts' ``daily_amount``.

Nothing here writes, and no approval logic is duplicated.
"""

from decimal import Decimal

from app.models.contract import ContractStatus
from app.services.contract_service import ContractService
from app.services.payment_service import PaymentService
from app.services.contract_reporting_service import ContractReportingService


_MONTH_DAYS = 30


def _rate(numerator: Decimal, denominator: Decimal) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator / denominator), 4)


class FinancialInsightService:

    def __init__(
        self,
        contract_service: ContractService,
        payment_service: PaymentService,
        contract_reporting_service: ContractReportingService,
    ):
        self.contract_service = contract_service
        self.payment_service = payment_service
        self.contract_reporting_service = contract_reporting_service

    # --- helpers ------------------------------------------------------------

    def _active_contracts(self, user_id: int):
        return self.contract_service.get_user_contracts(user_id, ContractStatus.ACTIVE)

    def _stats(self, user_id: int) -> dict:
        # Reuses the reporting service's totals (APPROVED-only balances).
        return self.contract_reporting_service.get_contract_stats(user_id)

    @staticmethod
    def _sum(values) -> Decimal:
        return sum(values, Decimal("0"))

    # --- capital / returns --------------------------------------------------

    def get_total_active_capital(self, user_id: int) -> Decimal:
        # Contractual value currently deployed in ACTIVE contracts.
        return self._sum(c.total_amount for c in self._active_contracts(user_id))

    def get_total_expected_return(self, user_id: int) -> Decimal:
        # Full contractual value across all of the user's contracts.
        return self._stats(user_id)["total_contract_value"]

    def get_total_collected(self, user_id: int) -> Decimal:
        stats = self._stats(user_id)
        return stats["total_contract_value"] - stats["total_remaining_amount"]

    def get_total_outstanding(self, user_id: int) -> Decimal:
        return self._stats(user_id)["total_remaining_amount"]

    def get_collection_rate(self, user_id: int) -> float:
        stats = self._stats(user_id)
        collected = stats["total_contract_value"] - stats["total_remaining_amount"]
        return _rate(collected, stats["total_contract_value"])

    # --- forward-looking income --------------------------------------------

    def get_daily_expected_income(self, user_id: int) -> Decimal:
        return self._sum(c.daily_amount for c in self._active_contracts(user_id))

    def get_monthly_expected_income(self, user_id: int) -> Decimal:
        return self.get_daily_expected_income(user_id) * _MONTH_DAYS

    def get_expected_next_month_income(self, user_id: int) -> Decimal:
        # Capped by each contract's remaining balance -- you can't collect more
        # than is still owed.
        total = Decimal("0")
        for contract in self._active_contracts(user_id):
            remaining = self.payment_service.calculate_remaining_amount(
                contract.total_amount, contract.id
            )
            month = contract.daily_amount * _MONTH_DAYS
            total += min(month, remaining)
        return total

    # --- roll-ups -----------------------------------------------------------

    def get_roi_summary(self, user_id: int) -> dict:
        stats = self._stats(user_id)
        collected = stats["total_contract_value"] - stats["total_remaining_amount"]
        return {
            "expected_return": stats["total_contract_value"],
            "collected": collected,
            "outstanding": stats["total_remaining_amount"],
            "collection_rate": _rate(collected, stats["total_contract_value"]),
        }

    def get_cashflow_summary(self, user_id: int) -> dict:
        stats = self._stats(user_id)
        collected = stats["total_contract_value"] - stats["total_remaining_amount"]
        return {
            "collected_to_date": collected,
            "outstanding": stats["total_remaining_amount"],
            "daily_expected_income": self.get_daily_expected_income(user_id),
            "monthly_expected_income": self.get_monthly_expected_income(user_id),
        }

    def get_financial_summary(self, user_id: int) -> dict:
        stats = self._stats(user_id)
        collected = stats["total_contract_value"] - stats["total_remaining_amount"]

        return {
            "active_contracts": stats["active_contracts"],
            "total_contracts": stats["total_contracts"],
            "total_active_capital": self.get_total_active_capital(user_id),
            "total_expected_return": stats["total_contract_value"],
            "total_collected": collected,
            "total_outstanding": stats["total_remaining_amount"],
            "collection_rate": _rate(collected, stats["total_contract_value"]),
            "daily_expected_income": self.get_daily_expected_income(user_id),
            "monthly_expected_income": self.get_monthly_expected_income(user_id),
        }
