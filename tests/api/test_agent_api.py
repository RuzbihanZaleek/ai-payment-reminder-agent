import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.agent import get_agent_execution_service
from app.agents.state import AgentState
from app.enums.reminder_decision import ReminderDecision


client = TestClient(app)


class FakeService:

    def __init__(self, state=None, exc=None):
        self.state = state
        self.exc = exc
        self.calls = []

    def execute(self, contract_id, message_id, message):

        self.calls.append((contract_id, message_id, message))

        if self.exc is not None:
            raise self.exc

        return self.state


@pytest.fixture
def override_service():

    services = {}

    def _install(service):
        services["service"] = service
        app.dependency_overrides[get_agent_execution_service] = lambda: service
        return service

    yield _install

    app.dependency_overrides.clear()


def test_successful_request(override_service):

    state = AgentState(
        message="I paid 100",
        decision=ReminderDecision.NO_REMINDER,
        generated_message="Thanks! I've recorded your payment.",
        requires_approval=False,
        notification_sent=True,
    )

    service = override_service(FakeService(state=state))

    response = client.post(
        "/agent/messages",
        json={
            "contract_id": 1,
            "message_id": "msg_1",
            "message": "I paid 100",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["decision"] == "NO_REMINDER"
    assert data["generated_message"] == "Thanks! I've recorded your payment."
    assert data["requires_approval"] is False
    assert data["notification_sent"] is True

    # The service received the validated request, unchanged
    assert service.calls == [(1, "msg_1", "I paid 100")]


def test_invalid_payload_returns_422(override_service):

    # contract_id must be an int; message is missing entirely
    override_service(FakeService())

    response = client.post(
        "/agent/messages",
        json={
            "contract_id": "not-an-int",
        },
    )

    assert response.status_code == 422


def test_execution_exception_returns_500(override_service):

    override_service(FakeService(exc=RuntimeError("workflow blew up")))

    response = client.post(
        "/agent/messages",
        json={
            "contract_id": 1,
            "message_id": "msg_1",
            "message": "I paid 100",
        },
    )

    assert response.status_code == 500
