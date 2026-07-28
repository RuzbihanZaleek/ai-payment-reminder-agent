"""Payment-behaviour insights (read-only).

Uses APPROVED payments only (``PaymentStatus.APPROVED`` -- the same "confirmed
money" rule PaymentService applies to balances). Reuses PaymentService for the
underlying payment data; the aggregation here (averages, trends, streaks, payer
rankings) is presentation analysis, not a business rule.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.enums.payment_status import PaymentStatus
from app.services.payment_service import PaymentService
from app.services.contract_service import ContractService


def _avg(total: Decimal, count: int) -> Decimal:
    if count <= 0:
        return Decimal("0")
    return (total / count).quantize(Decimal("0.01"))


class PaymentInsightService:

    def __init__(
        self,
        payment_service: PaymentService,
        contract_service: ContractService,
    ):
        self.payment_service = payment_service
        self.contract_service = contract_service

    # --- data ---------------------------------------------------------------

    def _approved_payments(self, user_id: int) -> list:
        # APPROVED status == confirmed money (matches balance calculations).
        return [
            p
            for p in self.payment_service.get_user_payments(user_id)
            if p.status == PaymentStatus.APPROVED
        ]

    @staticmethod
    def _span_days(payments) -> int:
        dates = [p.payment_date for p in payments]
        if not dates:
            return 0
        return (max(dates) - min(dates)).days + 1

    # --- summary / extremes -------------------------------------------------

    def get_payment_summary(self, user_id: int) -> dict:
        payments = self._approved_payments(user_id)
        amounts = [p.amount for p in payments]
        total = sum(amounts, Decimal("0"))
        return {
            "payment_count": len(payments),
            "total_amount": total,
            "average_payment": _avg(total, len(payments)),
            "largest_payment": max(amounts) if amounts else Decimal("0"),
            "smallest_payment": min(amounts) if amounts else Decimal("0"),
        }

    def get_average_payment(self, user_id: int) -> Decimal:
        return self.get_payment_summary(user_id)["average_payment"]

    def get_largest_payment(self, user_id: int) -> Decimal:
        return self.get_payment_summary(user_id)["largest_payment"]

    def get_smallest_payment(self, user_id: int) -> Decimal:
        return self.get_payment_summary(user_id)["smallest_payment"]

    # --- rate over time -----------------------------------------------------

    def _average_per(self, user_id: int, period_days: int) -> Decimal:
        payments = self._approved_payments(user_id)
        total = sum((p.amount for p in payments), Decimal("0"))
        span = self._span_days(payments)
        if span <= 0:
            return Decimal("0")
        periods = Decimal(span) / Decimal(period_days)
        if periods <= 0:
            return Decimal("0")
        return (total / periods).quantize(Decimal("0.01"))

    def get_average_daily_payment(self, user_id: int) -> Decimal:
        return self._average_per(user_id, 1)

    def get_average_weekly_payment(self, user_id: int) -> Decimal:
        return self._average_per(user_id, 7)

    def get_average_monthly_payment(self, user_id: int) -> Decimal:
        return self._average_per(user_id, 30)

    def get_payment_frequency(self, user_id: int) -> dict:
        payments = self._approved_payments(user_id)
        span = self._span_days(payments)
        per_day = round(len(payments) / span, 4) if span else 0.0
        return {"payment_count": len(payments), "span_days": span, "payments_per_day": per_day}

    # --- distribution / trends ----------------------------------------------

    def _by_month(self, payments) -> dict:
        buckets: dict[str, dict] = defaultdict(lambda: {"count": 0, "total": Decimal("0")})
        for p in payments:
            key = p.payment_date.strftime("%Y-%m")
            buckets[key]["count"] += 1
            buckets[key]["total"] += p.amount
        return buckets

    def get_payment_distribution(self, user_id: int) -> dict:
        return dict(self._by_month(self._approved_payments(user_id)))

    def get_payment_trends(self, user_id: int) -> list[dict]:
        buckets = self._by_month(self._approved_payments(user_id))
        return [
            {"month": month, "count": data["count"], "total": data["total"]}
            for month, data in sorted(buckets.items())
        ]

    def get_recent_payment_activity(self, user_id: int, limit: int = 10) -> list[dict]:
        payments = sorted(
            self._approved_payments(user_id),
            key=lambda p: p.payment_date,
            reverse=True,
        )
        return [
            {"payment_id": p.id, "contract_id": p.contract_id, "amount": p.amount,
             "payment_date": p.payment_date}
            for p in payments[:limit]
        ]

    def get_payment_streak(self, user_id: int) -> dict:
        days = sorted({p.payment_date for p in self._approved_payments(user_id)})
        if not days:
            return {"longest_streak_days": 0, "current_streak_days": 0}

        longest = current = 1
        for prev, curr in zip(days, days[1:]):
            if curr - prev == timedelta(days=1):
                current += 1
            else:
                current = 1
            longest = max(longest, current)

        # Current streak counts only if the most recent payment day is today/yesterday.
        current_streak = current if (date.today() - days[-1]).days <= 1 else 0
        return {"longest_streak_days": longest, "current_streak_days": current_streak}

    def get_payment_consistency(self, user_id: int) -> dict:
        payments = self._approved_payments(user_id)
        span = self._span_days(payments)
        payment_days = len({p.payment_date for p in payments})
        score = round(payment_days / span, 4) if span else 0.0
        return {"payment_days": payment_days, "span_days": span, "consistency_score": score}

    # --- payer rankings (per contract) --------------------------------------

    def _payer_stats(self, user_id: int) -> list[dict]:
        names = {
            c.id: {"name": c.name, "reference_code": c.reference_code}
            for c in self.contract_service.get_user_contracts(user_id)
        }

        grouped: dict[int, list] = defaultdict(list)
        for p in self._approved_payments(user_id):
            grouped[p.contract_id].append(p)

        stats = []
        for contract_id, payments in grouped.items():
            total = sum((p.amount for p in payments), Decimal("0"))
            dates = sorted(p.payment_date for p in payments)
            span = (dates[-1] - dates[0]).days if len(dates) > 1 else 0
            avg_gap = round(span / (len(dates) - 1), 2) if len(dates) > 1 else 0.0
            info = names.get(contract_id, {"name": None, "reference_code": None})
            stats.append(
                {
                    "contract_id": contract_id,
                    "name": info["name"],
                    "reference_code": info["reference_code"],
                    "total_paid": total,
                    "payment_count": len(payments),
                    "last_payment_date": dates[-1],
                    "average_gap_days": avg_gap,
                }
            )
        return stats

    def get_top_payers(self, user_id: int, limit: int = 5) -> list[dict]:
        stats = sorted(self._payer_stats(user_id), key=lambda s: s["total_paid"], reverse=True)
        return stats[:limit]

    def get_fastest_payers(self, user_id: int, limit: int = 5) -> list[dict]:
        # Smallest average gap between payments = fastest.
        stats = [s for s in self._payer_stats(user_id) if s["payment_count"] > 1]
        stats.sort(key=lambda s: s["average_gap_days"])
        return stats[:limit]

    def get_slowest_payers(self, user_id: int, limit: int = 5) -> list[dict]:
        # Largest gap since their last payment = slowest.
        stats = self._payer_stats(user_id)
        today = date.today()
        for s in stats:
            s["days_since_last_payment"] = (today - s["last_payment_date"]).days
        stats.sort(key=lambda s: s["days_since_last_payment"], reverse=True)
        return stats[:limit]
