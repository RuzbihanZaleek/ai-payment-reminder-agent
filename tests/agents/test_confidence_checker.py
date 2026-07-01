from decimal import Decimal

from app.agents.confidence_checker import ConfidenceChecker
from app.agents.state import AgentState
from app.schemas.payment_detection import (
    PaymentDetectionResult,
    PaymentIntent,
)


def create_state_with_confidence(confidence: float) -> AgentState:

    return AgentState(
        message="I paid 100 today",
        payment_detection=PaymentDetectionResult(
            intent=PaymentIntent.PAYMENT_RECEIVED,
            amount=Decimal("100"),
            currency="USD",
            confidence=confidence,
        ),
    )


def test_high_confidence_does_not_require_approval():

    checker = ConfidenceChecker()

    state = create_state_with_confidence(0.95)

    result = checker.check(state)

    assert result.requires_approval is False



def test_low_confidence_requires_approval():

    checker = ConfidenceChecker()

    state = create_state_with_confidence(0.50)

    result = checker.check(state)

    assert result.requires_approval is True



def test_missing_detection_requires_approval():

    checker = ConfidenceChecker()

    state = AgentState(
        message="Hello"
    )

    result = checker.check(state)

    assert result.requires_approval is True