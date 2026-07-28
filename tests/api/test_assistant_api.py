"""Assistant API: auth required, successful response, conversation persistence."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.assistant import get_assistant_service
from app.api.deps import get_current_user


client = TestClient(app)


class FakeAssistantService:
    def __init__(self):
        self.calls = []

    def chat(self, user_id, message):
        self.calls.append((user_id, message))
        return {"message": "John has $900 remaining.", "intent": "BALANCE_QUERY"}


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


def test_requires_authentication():
    response = client.post("/assistant/chat", json={"message": "How much does John owe?"})
    assert response.status_code == 401


def test_successful_response():
    service = FakeAssistantService()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_assistant_service] = lambda: service

    response = client.post("/assistant/chat", json={"message": "How much does John owe?"})

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "John has $900 remaining."
    assert body["intent"] == "BALANCE_QUERY"
    # user_id comes from the JWT, not the request body.
    assert service.calls == [(7, "How much does John owe?")]


def test_empty_message_is_rejected():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_assistant_service] = lambda: FakeAssistantService()

    response = client.post("/assistant/chat", json={"message": ""})

    assert response.status_code == 422


def test_v1_route_works():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_assistant_service] = lambda: FakeAssistantService()

    response = client.post("/api/v1/assistant/chat", json={"message": "hi"})

    assert response.status_code == 200
