"""Advisor API: authentication required + successful response."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.advisor import get_recommendation_service
from app.api.deps import get_current_user


client = TestClient(app)


class FakeRecommendationService:
    def __init__(self):
        self.calls = []

    def generate_personalized_recommendations(self, user_id):
        self.calls.append(user_id)
        return {
            "summary": "Your collection performance is improving",
            "financial_health": {"collection_rate": 0.72},
            "positives": ["5 contracts completed"],
            "risks": ["2 overdue contracts"],
            "suggestions": ["Review delayed customers"],
        }


@pytest.fixture(autouse=True)
def _cleanup():
    yield
    app.dependency_overrides.clear()


def test_requires_authentication():
    assert client.post("/advisor/analyze").status_code == 401


def test_successful_response():
    service = FakeRecommendationService()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_recommendation_service] = lambda: service

    response = client.post("/advisor/analyze")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == "Your collection performance is improving"
    assert body["risks"] == ["2 overdue contracts"]
    assert body["recommendations"] == ["Review delayed customers"]
    # user_id from the JWT.
    assert service.calls == [7]


def test_v1_route_works():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_recommendation_service] = lambda: FakeRecommendationService()

    assert client.post("/api/v1/advisor/analyze").status_code == 200
