"""MemoryExtractionService: preferences/patterns stored, normal queries ignored."""

from types import SimpleNamespace

from app.services.ai_memory import MemoryExtractionService, FinancialMemoryType


class FakeMemoryService:
    def __init__(self):
        self.remembered = []

    def remember(self, user_id, memory_type, content, confidence_score=1.0):
        record = SimpleNamespace(
            user_id=user_id, memory_type=memory_type, content=content
        )
        self.remembered.append(record)
        return record


def _extract(message):
    fake = FakeMemoryService()
    MemoryExtractionService(fake).extract(7, message)
    return fake.remembered


def test_detects_user_goal():
    remembered = _extract("I want monthly financial summaries")
    assert len(remembered) == 1
    assert remembered[0].memory_type == FinancialMemoryType.USER_GOAL


def test_detects_preference_phrasing():
    remembered = _extract("I prefer weekly collection reports")
    assert remembered[0].memory_type == FinancialMemoryType.USER_GOAL


def test_detects_financial_pattern():
    remembered = _extract("My customers often delay payments")
    assert len(remembered) == 1
    assert remembered[0].memory_type == FinancialMemoryType.FINANCIAL_PATTERN


def test_ignores_normal_question():
    assert _extract("How much does John owe?") == []


def test_ignores_listing_command():
    assert _extract("Show me my contracts") == []


def test_ignores_secrets():
    assert _extract("My password is hunter2 and I want reports") == []


def test_empty_message():
    assert _extract("   ") == []
