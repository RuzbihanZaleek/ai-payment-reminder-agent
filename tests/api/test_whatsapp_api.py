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
)


client = TestClient(app)


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

    def _install(contract_repository=None, service=None, processed_repository=None):
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
