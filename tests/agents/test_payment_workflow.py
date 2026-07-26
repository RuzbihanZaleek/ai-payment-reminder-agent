from app.agents.payment_workflow import PaymentWorkflow
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


class FakeConfidenceChecker:

    def __init__(self):
        self.executed = False

    def check(self, state):

        self.executed = True
        state.requires_approval = False

        return state


class FakePaymentCreationNode:

    def __init__(self):
        self.executed = False

    def execute(self, state):

        self.executed = True
        state.payment_id = 42

        return state


class FakeBalanceUpdateNode:

    def __init__(self):
        self.executed = False

    def execute(self, state):

        self.executed = True
        state.total_paid = 350
        state.remaining_amount = 650

        return state


def test_payment_workflow():

    confidence_checker = FakeConfidenceChecker()
    payment_creation_node = FakePaymentCreationNode()
    balance_update_node = FakeBalanceUpdateNode()

    workflow = PaymentWorkflow(
        FakePaymentAgent(),
        confidence_checker,
        payment_creation_node,
        balance_update_node
    )

    state = AgentState(
        message="Paid 100"
    )

    result = workflow.process(state)

    # Payment detection is added to state
    assert result.payment_detection is not None
    assert result.payment_detection.amount == 100

    # Confidence checker is executed
    assert confidence_checker.executed is True

    # Payment creation node is executed
    assert payment_creation_node.executed is True

    # Final state contains payment_id
    assert result.payment_id == 42

    # Balance update node is executed
    assert balance_update_node.executed is True

    # Final state contains updated balance
    assert result.total_paid == 350
    assert result.remaining_amount == 650
