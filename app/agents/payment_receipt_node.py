from app.agents.state import AgentState
from app.services.payment_receipt_service import PaymentReceiptService


class PaymentReceiptNode:
    """Orchestration only: delegates receipt snapshot creation to the service."""

    def __init__(
        self,
        payment_receipt_service: PaymentReceiptService,
    ):
        self.payment_receipt_service = payment_receipt_service

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        # No receipt for the approval path (no payment was created).
        if state.requires_approval:
            return state

        if not state.payment_allocations:
            return state

        state.payment_receipts = self.payment_receipt_service.generate_receipts(
            state.agent_run_id,
            state.payment_allocations,
        )

        return state