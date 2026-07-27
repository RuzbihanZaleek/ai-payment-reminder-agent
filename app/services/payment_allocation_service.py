from decimal import Decimal

from app.services.payment_service import PaymentService


class PaymentAllocationService:
    """Owns the payment-allocation algorithm.

    Given a payment amount and a set of candidate contracts, decides how the
    payment is split across them. No other component contains allocation rules.
    """

    def __init__(
        self,
        payment_service: PaymentService,
    ):
        self.payment_service = payment_service

    def allocate(
        self,
        amount,
        contracts: list,
        resolved_contract_id: int | None = None,
    ) -> dict:
        """Return {"allocations": [{contract_id, amount}], "requires_approval": bool}."""

        # Rule 1: an explicit reference already selected a single contract.
        if resolved_contract_id is not None:
            return self._single(resolved_contract_id, amount)

        # Guard: a non-positive amount cannot be allocated.
        if amount is None or amount <= 0:
            return self._needs_approval()

        # Rule 3 & 7: eligible contracts are those still owing money. Completed /
        # fully-paid contracts (remaining <= 0) are never allocated to.
        eligible = self._eligible(contracts)

        if not eligible:
            return self._needs_approval()

        # Rule 2: exactly one eligible contract -> full amount.
        if len(eligible) == 1:
            return self._single(eligible[0]["id"], amount)

        # Rule 4: distribute daily-amount units round-robin across contracts.
        allocations = self._round_robin(amount, eligible)

        # Rule 6: the amount did not divide evenly into daily units.
        if allocations is None:
            return self._needs_approval()

        return {"allocations": allocations, "requires_approval": False}

    def _eligible(self, contracts: list) -> list:

        eligible = []

        for contract in contracts or []:
            remaining = self.payment_service.calculate_remaining_amount(
                contract["total_amount"],
                contract["id"],
            )

            if remaining > 0:
                eligible.append(contract)

        return eligible

    def _round_robin(self, amount, eligible: list):

        remaining = amount
        totals = {contract["id"]: Decimal("0") for contract in eligible}

        while remaining > 0:
            progressed = False

            for contract in eligible:
                if remaining <= 0:
                    break

                daily = contract["daily_amount"]

                if remaining >= daily:
                    totals[contract["id"]] += daily
                    remaining -= daily
                    progressed = True

            # A full pass allocated nothing but money is left over -> the amount
            # is not a whole number of daily units.
            if not progressed:
                return None

        return [
            {"contract_id": contract_id, "amount": total}
            for contract_id, total in totals.items()
            if total > 0
        ]

    @staticmethod
    def _single(contract_id: int, amount) -> dict:
        return {
            "allocations": [{"contract_id": contract_id, "amount": amount}],
            "requires_approval": False,
        }

    @staticmethod
    def _needs_approval() -> dict:
        return {"allocations": [], "requires_approval": True}