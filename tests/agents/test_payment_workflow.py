from app.agents.payment_workflow import PaymentWorkflow
from app.agents.payment_message_agent import PaymentMessageAgent
from app.agents.state import AgentState


class FakePaymentAgent:

    def analyze_message(self, message):

        from app.schemas.payment_detection import PaymentDetectionResult
        
        from app.enums.payment_detection import PaymentIntent

        return PaymentDetectionResult(
            intent=PaymentIntent.PAYMENT_RECEIVED,
            amount=100,
            currency="USD",
            confidence=0.95
        )


def test_payment_workflow():

    workflow = PaymentWorkflow(
        FakePaymentAgent()
    )

    state = AgentState(
        message="Paid 100"
    )

    result = workflow.process(state)

    assert result.payment_detection is not None

    assert result.payment_detection.amount == 100