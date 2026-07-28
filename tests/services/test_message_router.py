from app.enums.payment_detection import PaymentIntent
from app.services.message_router_service import MessageRouterService


class FakeDetection:
    def __init__(self, intent):
        self.intent = intent


class FakePaymentAgent:
    def __init__(self, intent):
        self.intent = intent
        self.calls = []

    def analyze_message(self, message, history=None):
        self.calls.append((message, history))
        return FakeDetection(self.intent)


def test_payment_message_is_payment():
    router = MessageRouterService(FakePaymentAgent(PaymentIntent.PAYMENT_RECEIVED))
    assert router.is_payment("I paid 100", []) is True


def test_non_payment_message_is_not_payment():
    router = MessageRouterService(FakePaymentAgent(PaymentIntent.NOT_PAYMENT))
    assert router.is_payment("how much does John owe?", []) is False


def test_unknown_routes_to_assistant():
    router = MessageRouterService(FakePaymentAgent(PaymentIntent.UNKNOWN))
    # Anything that isn't a clear payment goes to the assistant.
    assert router.is_payment("hello", []) is False


def test_history_is_forwarded():
    agent = FakePaymentAgent(PaymentIntent.NOT_PAYMENT)
    MessageRouterService(agent).is_payment("hi", [{"role": "USER", "content": "x"}])
    assert agent.calls[0][1] == [{"role": "USER", "content": "x"}]
