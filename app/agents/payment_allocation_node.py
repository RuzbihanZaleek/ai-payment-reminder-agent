from app.agents.state import AgentState
from app.services.payment_allocation_service import PaymentAllocationService


class PaymentAllocationNode:
    """Orchestration only: delegates allocation to PaymentAllocationService."""

    def __init__(
        self,
        payment_allocation_service: PaymentAllocationService,
    ):
        self.payment_allocation_service = payment_allocation_service

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        detection = state.payment_detection

        if detection is None or detection.amount is None:
            return state

        # Respect an approval already required (low confidence, ambiguous
        # references) -- do not auto-allocate in that case.
        if state.requires_approval:
            return state

        result = self.payment_allocation_service.allocate(
            detection.amount,
            state.resolved_contracts,
            resolved_contract_id=state.contract_id,
        )

        state.payment_allocations = result["allocations"]

        if result["requires_approval"]:
            state.requires_approval = True

        return state