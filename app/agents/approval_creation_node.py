from datetime import date

from app.agents.state import AgentState
from app.enums.payment_source import PaymentSource
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.models.payment import Payment
from app.services.payment_service import PaymentService


class ApprovalCreationNode:

    def __init__(
        self,
        payment_service: PaymentService,
    ):
        self.payment_service = payment_service

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        # Only low-confidence payments need a human-approval record.
        if not state.requires_approval:
            return state

        # Cannot create a pending Payment without a contract (payments.contract_id
        # is NOT NULL). This happens for ambiguous / unknown / uneven multi-contract
        # cases where no single contract was resolved -> keep approval, do nothing.
        if state.contract_id is None:
            return state

        detection = state.payment_detection

        if detection is None or detection.amount is None:
            return state

        # Create a PENDING payment awaiting approval -- never an approved one.
        payment = Payment(
            contract_id=state.contract_id,
            amount=detection.amount,
            payment_date=state.pending_dates[0]
            if state.pending_dates
            else date.today(),
            status=PaymentStatus.PENDING,
            approval_status=ApprovalStatus.PENDING,
            source=PaymentSource.WHATSAPP_AI,
            reference_message_id=state.message_id,
            notes=state.message,
        )

        self.payment_service.create_payment(payment)

        return state
