from decimal import Decimal

from app.agents.payment_message_agent import (
    PaymentMessageAgent
)

from app.enums.payment_detection import (
    PaymentIntent
)


class FakeLLM:

    def invoke(self, message):

        return {
            "intent": "PAYMENT_RECEIVED",
            "amount": Decimal("100"),
            "currency": "USD",
            "confidence": 0.95
        }


def test_payment_message_agent():

    agent = PaymentMessageAgent(
        FakeLLM()
    )

    result = agent.analyze_message(
        "I sent 100 today"
    )

    assert result.intent == PaymentIntent.PAYMENT_RECEIVED

    assert result.amount == Decimal("100")