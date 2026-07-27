from datetime import date

from app.agents.state import AgentState
from app.enums.payment_source import PaymentSource
from app.enums.approval_status import ApprovalStatus
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
            # These payments were auto-processed (no manual approval required),
            # so they are confirmed on creation and count as received.
            payment = Payment(
                contract_id=allocation["contract_id"],
                amount=allocation["amount"],
                payment_date=payment_date,
                approval_status=ApprovalStatus.APPROVED,
                requires_manual_review=False,
                source=PaymentSource.WHATSAPP_AI,
                reference_message_id=state.message_id,
                notes=state.message,
            )

            created_payment = self.payment_service.create_payment(payment)
            created_ids.append(created_payment.id)

            # Link the created payment back to its allocation so the receipt
            # node can reference it.
            allocation["payment_id"] = created_payment.id

        # First created id kept for the single-payment gate used downstream.
        if created_ids:
            state.payment_id = created_ids[0]

        return state