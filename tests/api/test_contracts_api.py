from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.api.contracts import get_contract_service
from app.api.deps import get_current_user


client = TestClient(app)


@pytest.fixture(autouse=True)
def _auth():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    yield
    app.dependency_overrides.clear()


class FakeContractService:
    """Records the create call and returns a contract-like object."""

    def __init__(self, exc=None):
        self.exc = exc
        self.created_with = None

    def create_contract(self, payload, user_id=None):

        self.created_with = (payload, user_id)

        if self.exc is not None:
            raise self.exc

        now = datetime(2026, 7, 30, tzinfo=timezone.utc)

        return SimpleNamespace(
            id=1,
            reference_code=payload.reference_code,
            name=payload.name,
            description=payload.description,
            total_amount=payload.total_amount,
            daily_amount=payload.daily_amount,
            currency=payload.currency.value,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status="ACTIVE",
            whatsapp_chat_id=payload.whatsapp_chat_id,
            created_at=now,
            updated_at=now,
        )


def _payload(**overrides):
    body = {
        "reference_code": "LOAN-001",
        "name": "Nok",
        "total_amount": "1100",
        "daily_amount": "10",
        "currency": "USD",
        "start_date": "2026-07-03",
        "whatsapp_chat_id": "66849742572",
    }
    body.update(overrides)
    return body


def test_create_contract_success():

    service = FakeContractService()
    app.dependency_overrides[get_contract_service] = lambda: service

    response = client.post("/contracts", json=_payload())

    assert response.status_code == 201

    data = response.json()
    assert data["id"] == 1
    assert data["reference_code"] == "LOAN-001"
    assert data["status"] == "ACTIVE"
    assert data["whatsapp_chat_id"] == "66849742572"

    # Owner is taken from the JWT, not the request body.
    payload, user_id = service.created_with
    assert user_id == 7
    assert payload.total_amount == Decimal("1100")


def test_create_contract_duplicate_reference_returns_409():

    service = FakeContractService(exc=IntegrityError("stmt", {}, Exception("dup")))
    app.dependency_overrides[get_contract_service] = lambda: service

    response = client.post("/contracts", json=_payload())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_REFERENCE"


def test_create_contract_requires_auth():

    app.dependency_overrides.pop(get_current_user, None)

    response = client.post("/contracts", json=_payload())

    assert response.status_code == 401


def test_create_contract_rejects_daily_greater_than_total():

    service = FakeContractService()
    app.dependency_overrides[get_contract_service] = lambda: service

    # daily_amount > total_amount is rejected by the ContractCreate validator.
    response = client.post(
        "/contracts", json=_payload(total_amount="50", daily_amount="100")
    )

    assert response.status_code == 422
    assert service.created_with is None


def test_create_contract_available_under_v1_prefix():

    service = FakeContractService()
    app.dependency_overrides[get_contract_service] = lambda: service

    response = client.post("/api/v1/contracts", json=_payload())

    assert response.status_code == 201
