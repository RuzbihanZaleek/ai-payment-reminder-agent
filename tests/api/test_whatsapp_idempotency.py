import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.agent import get_agent_execution_service
from app.api.whatsapp import (
    get_contract_repository,
    get_processed_message_repository,
    get_conversation_memory_service,
)


client = TestClient(app)


class FakeContract:

    def __init__(self, contract_id=7):
        self.id = contract_id


class FakeContractRepository:

    def get_by_whatsapp_chat_id(self, whatsapp_chat_id):

        return FakeContract()


class FakeConversation:

    def __init__(self, conversation_id=1):
        self.id = conversation_id


class FakeConversationMemoryService:

    def get_or_create_conversation(self, whatsapp_chat_id):

        return FakeConversation()

    def store_user_message(self, conversation_id, content):
        pass

    def get_history(self, conversation_id, limit=10):

        return {"summary": None, "messages": []}

    def store_assistant_message(self, conversation_id, content):
        pass


class FakeService:

    def __init__(self, exc=None):
        self.exc = exc
        self.calls = []

    def execute(
        self,
        contract_id,
        message_id,
        message,
        conversation_id=None,
        conversation_history=None,
    ):

        self.calls.append((contract_id, message_id, message))

        if self.exc is not None:
            raise self.exc


class FakeProcessedMessageRepository:

    def __init__(self, already_seen=False):
        self.already_seen = already_seen
        self.created = []

    def exists(self, message_id):

        return self.already_seen

    def create(self, message_id, source):

        self.created.append((message_id, source))


def _install(contract_repo, processed_repo, service):

    app.dependency_overrides[get_contract_repository] = lambda: contract_repo
    app.dependency_overrides[get_processed_message_repository] = lambda: processed_repo
    app.dependency_overrides[get_conversation_memory_service] = (
        lambda: FakeConversationMemoryService()
    )
    app.dependency_overrides[get_agent_execution_service] = lambda: service


def _payload(message_id="wamid.123"):

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
                                    "text": {"body": "I paid 100"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture(autouse=True)
def _clear_overrides():

    yield

    app.dependency_overrides.clear()


def test_first_message_executes_and_is_stored():

    processed_repo = FakeProcessedMessageRepository(already_seen=False)
    service = FakeService()

    _install(FakeContractRepository(), processed_repo, service)

    response = client.post("/webhook", json=_payload("wamid.first"))

    assert response.status_code == 200

    # Workflow ran...
    assert service.calls == [(7, "wamid.first", "I paid 100")]
    # ...and the message was recorded as processed.
    assert processed_repo.created == [("wamid.first", "whatsapp")]


def test_duplicate_message_is_not_reprocessed():

    processed_repo = FakeProcessedMessageRepository(already_seen=True)
    service = FakeService()

    _install(FakeContractRepository(), processed_repo, service)

    response = client.post("/webhook", json=_payload("wamid.dupe"))

    assert response.status_code == 200

    # Workflow must NOT run, and nothing new is stored.
    assert service.calls == []
    assert processed_repo.created == []


def test_failed_execution_is_not_stored():

    processed_repo = FakeProcessedMessageRepository(already_seen=False)
    service = FakeService(exc=RuntimeError("workflow blew up"))

    _install(FakeContractRepository(), processed_repo, service)

    response = client.post("/webhook", json=_payload("wamid.fail"))

    # Still 200 to Meta...
    assert response.status_code == 200
    # ...workflow was attempted...
    assert len(service.calls) == 1
    # ...but the message is NOT marked processed, so a retry can reprocess it.
    assert processed_repo.created == []