import pytest
from fastapi.testclient import TestClient

from types import SimpleNamespace

from app.main import app
from app.core.config import settings
from app.api.agent import get_agent_execution_service
from app.api.whatsapp import (
    get_contract_repository,
    get_processed_message_repository,
    get_conversation_memory_service,
    get_message_router,
    get_assistant_service,
    get_whatsapp_notification_service,
)


client = TestClient(app)


class FakeRouter:
    def __init__(self, is_payment=True):
        self._is_payment = is_payment
        self.calls = []

    def is_payment(self, message, history=None):
        self.calls.append(message)
        return self._is_payment


class FakeAssistant:
    def __init__(self, message="AI reply"):
        self.message = message
        self.calls = []

    def chat(self, user_id, message, conversation_key=None, action_authorizer=None):
        self.calls.append((user_id, message, conversation_key))
        self.authorizer = action_authorizer
        return {"message": self.message, "intent": "UNKNOWN"}


class FakeWhatsAppNotification:
    def __init__(self):
        self.sent = []

    def send(self, recipient, message):
        self.sent.append((recipient, message))
        return True


class FakeConversation:

    def __init__(self, conversation_id=1):
        self.id = conversation_id


class FakeConversationMemoryService:

    def __init__(self):
        self.user_messages = []
        self.assistant_messages = []

    def get_or_create_conversation(self, whatsapp_chat_id):

        return FakeConversation()

    def store_user_message(self, conversation_id, content):

        self.user_messages.append((conversation_id, content))

    def get_history(self, conversation_id, limit=10):

        return {"summary": None, "messages": []}

    def store_assistant_message(self, conversation_id, content):

        self.assistant_messages.append((conversation_id, content))


class FakeContract:

    def __init__(self, contract_id, reference_code="INV001", user_id=1):
        self.id = contract_id
        self.user_id = user_id
        self.reference_code = reference_code
        self.total_amount = 1000
        self.daily_amount = 10
        self.whatsapp_chat_id = "chat"


class FakeContractRepository:

    def __init__(self, contract=None):
        self.contract = contract
        self.lookups = []

    def get_active_by_whatsapp_chat_id(self, whatsapp_chat_id):

        self.lookups.append(whatsapp_chat_id)

        return [self.contract] if self.contract is not None else []


class FakeService:

    def __init__(self, exc=None, generated_message=None):
        self.exc = exc
        self.generated_message = generated_message
        self.calls = []

    def execute(
        self,
        contract_id,
        message_id,
        message,
        conversation_id=None,
        conversation_history=None,
        resolved_contracts=None,
    ):

        self.calls.append((contract_id, message_id, message))

        if self.exc is not None:
            raise self.exc

        return SimpleNamespace(generated_message=self.generated_message)


class FakeProcessedMessageRepository:

    def __init__(self, already_seen=False):
        self.already_seen = already_seen
        self.created = []

    def exists(self, message_id):

        return self.already_seen

    def create(self, message_id, source):

        self.created.append((message_id, source))


def _message_payload(
    message_id="wamid.123",
    phone="15551234567",
    body="I paid 100",
):

    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": phone,
                                    "text": {"body": body},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture
def overrides():

    def _install(
        contract_repository=None,
        service=None,
        processed_repository=None,
        router=None,
        assistant=None,
        notification=None,
    ):
        if contract_repository is not None:
            app.dependency_overrides[get_contract_repository] = (
                lambda: contract_repository
            )
        if service is not None:
            app.dependency_overrides[get_agent_execution_service] = (
                lambda: service
            )

        # Default to a repository that has never seen the message, so tests
        # that don't care about idempotency behave as before.
        processed_repository = processed_repository or FakeProcessedMessageRepository()
        app.dependency_overrides[get_processed_message_repository] = (
            lambda: processed_repository
        )

        # Conversation memory is not the focus of these tests -> use a stub.
        app.dependency_overrides[get_conversation_memory_service] = (
            lambda: FakeConversationMemoryService()
        )

        # Router defaults to "payment" so existing payment tests are unchanged.
        router = router or FakeRouter(is_payment=True)
        app.dependency_overrides[get_message_router] = lambda: router
        app.dependency_overrides[get_assistant_service] = (
            lambda: assistant or FakeAssistant()
        )
        app.dependency_overrides[get_whatsapp_notification_service] = (
            lambda: notification or FakeWhatsAppNotification()
        )

    yield _install

    app.dependency_overrides.clear()


def test_webhook_verification_success(monkeypatch):

    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test-token")

    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-token",
            "hub.challenge": "CHALLENGE_123",
        },
    )

    assert response.status_code == 200
    assert response.text == "CHALLENGE_123"


def test_invalid_verification_token(monkeypatch):

    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test-token")

    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "CHALLENGE_123",
        },
    )

    assert response.status_code == 403


def test_valid_incoming_message(overrides):

    repo = FakeContractRepository(contract=FakeContract(contract_id=7))
    service = FakeService()

    overrides(contract_repository=repo, service=service)

    response = client.post(
        "/webhook",
        json=_message_payload(
            message_id="wamid.abc",
            phone="15559999999",
            body="I paid 250",
        ),
    )

    assert response.status_code == 200

    # Contract resolved by sender phone, then service invoked with its id
    assert repo.lookups == ["15559999999"]
    assert service.calls == [(7, "wamid.abc", "I paid 250")]


# --- /webhooks/whatsapp path alias (Phase 2) --------------------------------

def test_webhook_verification_success_on_whatsapp_alias(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test-token")

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-token",
            "hub.challenge": "CHALLENGE_123",
        },
    )

    assert response.status_code == 200
    assert response.text == "CHALLENGE_123"


def test_invalid_verification_token_on_whatsapp_alias(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test-token")

    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "CHALLENGE_123",
        },
    )

    assert response.status_code == 403


def test_incoming_message_on_whatsapp_alias(overrides):
    # The alias reuses the exact same handler as /webhook.
    repo = FakeContractRepository(contract=FakeContract(contract_id=7))
    service = FakeService()

    overrides(contract_repository=repo, service=service)

    response = client.post(
        "/webhooks/whatsapp",
        json=_message_payload(
            message_id="wamid.alias",
            phone="15559999999",
            body="I paid 250",
        ),
    )

    assert response.status_code == 200
    assert service.calls == [(7, "wamid.alias", "I paid 250")]


def test_payload_without_messages(overrides):

    repo = FakeContractRepository(contract=FakeContract(contract_id=7))
    service = FakeService()

    overrides(contract_repository=repo, service=service)

    # A status-update style event carries no "messages"
    payload = {
        "entry": [
            {"changes": [{"value": {"statuses": [{"id": "wamid.x"}]}}]}
        ]
    }

    response = client.post("/webhook", json=payload)

    assert response.status_code == 200
    assert service.calls == []


def test_unknown_phone_number(overrides):

    repo = FakeContractRepository(contract=None)
    service = FakeService()

    overrides(contract_repository=repo, service=service)

    response = client.post(
        "/webhook",
        json=_message_payload(phone="10000000000"),
    )

    assert response.status_code == 200
    assert repo.lookups == ["10000000000"]
    assert service.calls == []


def test_execution_exception_still_returns_200(overrides):

    repo = FakeContractRepository(contract=FakeContract(contract_id=7))
    service = FakeService(exc=RuntimeError("workflow blew up"))

    overrides(contract_repository=repo, service=service)

    response = client.post(
        "/webhook",
        json=_message_payload(),
    )

    assert response.status_code == 200
    assert len(service.calls) == 1


# --- Message routing (Phase 12.0) -------------------------------------------

def test_payment_message_routes_to_payment_workflow(overrides):
    repo = FakeContractRepository(contract=FakeContract(contract_id=7))
    service = FakeService()
    assistant = FakeAssistant()

    overrides(
        contract_repository=repo, service=service,
        router=FakeRouter(is_payment=True), assistant=assistant,
    )

    response = client.post("/webhook", json=_message_payload(body="I paid 100"))

    assert response.status_code == 200
    assert len(service.calls) == 1   # payment workflow ran
    assert assistant.calls == []      # assistant NOT invoked


def test_non_payment_message_routes_to_assistant(overrides):
    repo = FakeContractRepository(contract=FakeContract(contract_id=7, user_id=1))
    service = FakeService()
    assistant = FakeAssistant(message="You have 3 active contracts.")
    notification = FakeWhatsAppNotification()

    overrides(
        contract_repository=repo, service=service,
        router=FakeRouter(is_payment=False), assistant=assistant, notification=notification,
    )

    response = client.post(
        "/webhook", json=_message_payload(phone="15559999999", body="How am I doing?")
    )

    assert response.status_code == 200
    # Payment workflow NOT run; assistant handled it (scoped to owner user 1).
    assert service.calls == []
    assert assistant.calls == [(1, "How am I doing?", "15559999999")]
    # The AI reply was delivered over WhatsApp to the sender.
    assert notification.sent == [("15559999999", "You have 3 active contracts.")]


def test_whatsapp_create_contract_request_is_rejected(overrides):
    # End-to-end: a non-payment WRITE request over WhatsApp must be denied by the
    # guard -- no PendingAction created, a deny message delivered.
    from app.ai.assistant.assistant_service import AssistantService
    from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult
    from app.services.whatsapp_authorization_service import WhatsAppAuthorizationService
    from app.api.whatsapp import get_assistant_service, get_whatsapp_authorization_service

    class _Mem:
        def get_or_create_conversation(self, key):
            return SimpleNamespace(id=1)

        def get_recent_history(self, cid, limit=10):
            return []

        def store_user_message(self, cid, content):
            pass

        def store_assistant_message(self, cid, content):
            pass

    class _Tools:
        def gather(self, intent_result, user_id):
            return {"context": {}, "tool_calls": []}

    class _LLM:
        def detect_intent(self, message, history=None):
            return IntentDetectionResult(
                intent=AssistantIntent.CREATE_CONTRACT, person="John",
                amount=1200, daily_amount=20, phone="94771234567",
            )

        def generate(self, *args):
            return "n/a"

    class _Actions:
        def __init__(self):
            self.proposed = []

        def get_latest_pending(self, user_id):
            return None

        def propose(self, user_id, action_type, params):
            self.proposed.append(action_type)
            return {"message": "proposed", "created": True}

        def confirm_and_execute(self, user_id):
            return {"success": False, "message": "nothing"}

        def cancel_latest(self, user_id):
            return {"success": False, "message": "nothing"}

    actions = _Actions()
    real_assistant = AssistantService(_Mem(), _Tools(), _LLM(), action_service=actions)
    notification = FakeWhatsAppNotification()

    repo = FakeContractRepository(contract=FakeContract(contract_id=7, user_id=1))
    overrides(
        contract_repository=repo, service=FakeService(),
        router=FakeRouter(is_payment=False), notification=notification,
    )
    app.dependency_overrides[get_assistant_service] = lambda: real_assistant
    app.dependency_overrides[get_whatsapp_authorization_service] = (
        lambda: WhatsAppAuthorizationService()
    )

    response = client.post(
        "/webhook",
        json=_message_payload(phone="15559999999", body="Create a contract for John"),
    )

    assert response.status_code == 200
    assert actions.proposed == []                      # no write proposed
    assert notification.sent                            # a reply was delivered
    assert "authenticated app" in notification.sent[0][1]


# --- Tenant isolation (Phase 10.2) ------------------------------------------

class FakeMultiContractRepository:
    """Returns a fixed list of contracts for any phone lookup."""

    def __init__(self, contracts):
        self.contracts = contracts
        self.lookups = []

    def get_active_by_whatsapp_chat_id(self, whatsapp_chat_id):
        self.lookups.append(whatsapp_chat_id)
        return list(self.contracts)


class CapturingService:
    """Captures the resolved_contracts candidate pool handed to the workflow."""

    def __init__(self):
        self.resolved_contracts = None

    def execute(
        self,
        contract_id,
        message_id,
        message,
        conversation_id=None,
        conversation_history=None,
        resolved_contracts=None,
    ):
        self.resolved_contracts = resolved_contracts
        return SimpleNamespace(generated_message=None)


def test_phone_shared_across_users_scopes_to_owning_user(overrides):
    # Same phone matches contracts owned by two different users. The webhook must
    # derive the owning user from the first match and only expose that user's
    # contracts to the workflow -- never mix tenants in one run.
    owner_a = FakeContract(contract_id=1, reference_code="A1", user_id=1)
    owner_a_second = FakeContract(contract_id=2, reference_code="A2", user_id=1)
    owner_b = FakeContract(contract_id=3, reference_code="B1", user_id=2)

    repo = FakeMultiContractRepository([owner_a, owner_a_second, owner_b])
    service = CapturingService()

    overrides(contract_repository=repo, service=service)

    response = client.post("/webhook", json=_message_payload())

    assert response.status_code == 200

    resolved_ids = {c["id"] for c in service.resolved_contracts}
    # User 1 owns the first match, so only their two contracts are candidates.
    assert resolved_ids == {1, 2}
