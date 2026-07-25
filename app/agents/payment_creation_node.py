from app.agents.state import AgentState
from app.enums.payment_source import PaymentSource
from app.schemas.payment import PaymentCreate
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

        # Stop if manual approval is required
        if state.requires_approval:
            return state

        detection = state.payment_detection

        if detection is None or detection.amount is None:
            return state

        payment = PaymentCreate(
            contract_id=state.contract_id,
            amount=detection.amount,
            payment_date=state.pending_dates[0]
            if state.pending_dates
            else None,
            source=PaymentSource.WHATSAPP_AI,
            reference_message_id=state.message_id,
            notes=state.message,
        )

        created_payment = self.payment_service.create_payment(
            payment
        )

        state.payment_id = created_payment.id

        return state