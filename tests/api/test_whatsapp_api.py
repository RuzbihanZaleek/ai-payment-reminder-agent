import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.api.agent import get_agent_execution_service
from app.api.whatsapp import get_contract_repository


client = TestClient(app)


class FakeContract:

    def __init__(self, contract_id):
        self.id = contract_id


class FakeContractRepository:

    def __init__(self, contract=None):
        self.contract = contract
        self.lookups = []

    def get_by_whatsapp_chat_id(self, whatsapp_chat_id):

        self.lookups.append(whatsapp_chat_id)

        return self.contract


class FakeService:

    def __init__(self, exc=None):
        self.exc = exc
        self.calls = []

    def execute(self, contract_id, message_id, message):

        self.calls.append((contract_id, message_id, message))

        if self.exc is not None:
            raise self.exc

        return None


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

    installed = {}

    def _install(contract_repository=None, service=None):
        if contract_repository is not None:
            app.dependency_overrides[get_contract_repository] = (
                lambda: contract_repository
            )
            installed["repo"] = contract_repository
        if service is not None:
            app.dependency_overrides[get_agent_execution_service] = (
                lambda: service
            )
            installed["service"] = service

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
