from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
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


class _PaymentRouter:
    def is_payment(self, message, history=None):
        return True


class _StubAssistant:
    def chat(self, user_id, message, conversation_key=None, action_authorizer=None):
        return {"message": "ai", "intent": "UNKNOWN"}


class _StubNotify:
    def send(self, recipient, message):
        return True


def _install_routing_stubs():
    # These tests exercise the payment path; stub routing so no real LLM/DB is hit.
    app.dependency_overrides[get_message_router] = lambda: _PaymentRouter()
    app.dependency_overrides[get_assistant_service] = lambda: _StubAssistant()
    app.dependency_overrides[get_whatsapp_notification_service] = lambda: _StubNotify()


class FakeContract:

    def __init__(self, contract_id=7, user_id=1):
        self.id = contract_id
        self.user_id = user_id
        self.reference_code = "INV001"
        self.total_amount = 1000
        self.daily_amount = 10
        self.whatsapp_chat_id = "chat"


class FakeContractRepository:

    def get_active_by_whatsapp_chat_id(self, whatsapp_chat_id):

        return [FakeContract()]


class FakeProcessedMessageRepository:

    def __init__(self):
        self.created = []

    def exists(self, message_id):
        return False

    def create(self, message_id, source):
        self.created.append((message_id, source))


class FakeConversation:

    def __init__(self, conversation_id=55):
        self.id = conversation_id


class RecordingMemoryService:

    def __init__(self):
        self.user_messages = []
        self.assistant_messages = []
        self.history_requests = []

    def get_or_create_conversation(self, whatsapp_chat_id):

        self.chat_id = whatsapp_chat_id

        return FakeConversation()

    def store_user_message(self, conversation_id, content):

        self.user_messages.append((conversation_id, content))

    def get_history(self, conversation_id, limit=10):

        self.history_requests.append(conversation_id)

        return {
            "summary": None,
            "messages": [{"role": "USER", "content": "earlier message"}],
        }

    def store_assistant_message(self, conversation_id, content):

        self.assistant_messages.append((conversation_id, content))


class FakeService:

    def __init__(self, generated_message="Thanks, recorded.", exc=None):
        self.generated_message = generated_message
        self.exc = exc
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

        self.calls.append(
            {
                "contract_id": contract_id,
                "message_id": message_id,
                "message": message,
                "conversation_id": conversation_id,
                "conversation_history": conversation_history,
            }
        )

        if self.exc is not None:
            raise self.exc

        return SimpleNamespace(generated_message=self.generated_message)


def _payload(message_id="wamid.conv", body="I paid 100"):

    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": "15551234567",
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
def memory_and_service():

    memory = RecordingMemoryService()
    service = FakeService()

    app.dependency_overrides[get_contract_repository] = lambda: FakeContractRepository()
    app.dependency_overrides[get_processed_message_repository] = (
        lambda: FakeProcessedMessageRepository()
    )
    app.dependency_overrides[get_conversation_memory_service] = lambda: memory
    app.dependency_overrides[get_agent_execution_service] = lambda: service
    _install_routing_stubs()

    yield memory, service

    app.dependency_overrides.clear()


def test_stores_incoming_user_message(memory_and_service):

    memory, service = memory_and_service

    response = client.post("/webhook", json=_payload(body="I paid 100"))

    assert response.status_code == 200

    # The incoming message is stored against the conversation...
    assert memory.user_messages == [(55, "I paid 100")]

    # ...and the loaded history is handed to the agent.
    assert service.calls[0]["conversation_id"] == 55
    assert service.calls[0]["conversation_history"] == [
        {"role": "USER", "content": "earlier message"}
    ]


def test_stores_assistant_response(memory_and_service):

    memory, service = memory_and_service

    response = client.post("/webhook", json=_payload())

    assert response.status_code == 200

    # The agent's generated reply is persisted as an assistant message.
    assert memory.assistant_messages == [(55, "Thanks, recorded.")]


def test_failed_execution_stores_no_messages():

    memory = RecordingMemoryService()
    service = FakeService(exc=RuntimeError("workflow blew up"))
    processed = FakeProcessedMessageRepository()

    app.dependency_overrides[get_contract_repository] = lambda: FakeContractRepository()
    app.dependency_overrides[get_processed_message_repository] = lambda: processed
    app.dependency_overrides[get_conversation_memory_service] = lambda: memory
    app.dependency_overrides[get_agent_execution_service] = lambda: service
    _install_routing_stubs()

    try:
        response = client.post("/webhook", json=_payload())
    finally:
        app.dependency_overrides.clear()

    # Still 200 to Meta, but nothing was persisted...
    assert response.status_code == 200
    assert memory.user_messages == []
    assert memory.assistant_messages == []
    # ...and the message is not marked processed, so a retry can reprocess it.
    assert processed.created == []