from datetime import date

from app.agents.state import AgentState
from app.enums.payment_source import PaymentSource
from app.models.payment import Payment
from app.services.payment_service import PaymentService


class PaymentCreationNode:

    def __init__(
        self,
        payment_service: PaymentService,
    ):
        self.payment_service = payment_service

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        # Stop if manual approval is required.
        if state.requires_approval:
            return state

        # Persist one Payment per allocation produced by PaymentAllocationNode.
        if not state.payment_allocations:
            return state

        payment_date = (
            state.pending_dates[0] if state.pending_dates else date.today()
        )

        created_ids = []

        for allocation in state.payment_allocations:
            payment = Payment(
                contract_id=allocation["contract_id"],
                amount=allocation["amount"],
                payment_date=payment_date,
                source=PaymentSource.WHATSAPP_AI,
                reference_message_id=state.message_id,
                notes=state.message,
            )

            created_payment = self.payment_service.create_payment(payment)
            created_ids.append(created_payment.id)

        # First created id kept for the single-payment gate used downstream.
        if created_ids:
            state.payment_id = created_ids[0]

        return state