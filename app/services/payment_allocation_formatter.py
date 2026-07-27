from decimal import Decimal


class PaymentAllocationFormatter:
    """Converts payment allocations into human-readable text.

    Works purely off the allocation objects (which carry reference_code), so no
    database access is required to render a response.
    """

    def format(self, allocations: list) -> str:

        lines = []

        for allocation in allocations:
            reference_code = allocation.get("reference_code") or "Contract"
            amount = allocation.get("amount")

            lines.append(f"{reference_code}: {self._format_money(amount)}")

        return "\n".join(lines)

    @staticmethod
    def _format_money(amount) -> str:

        if amount is None:
            return "$0"

        amount = Decimal(amount)

        # Whole amounts render without decimals ($20, $2,100); otherwise cents.
        if amount == amount.to_integral_value():
            return f"${amount:,.0f}"

        return f"${amount:,.2f}"