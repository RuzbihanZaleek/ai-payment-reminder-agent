"""Decide whether a conversation turn should become long-term memory.

Deterministic, rule-based extraction (no LLM, fully testable): it recognizes
stated preferences/goals and described financial patterns, and ignores ordinary
financial questions ("how much does John owe?"). Secrets are never stored.
"""

import re

from app.core.logger import get_logger
from app.services.ai_memory.financial_memory_service import FinancialMemoryService
from app.services.ai_memory.memory_types import FinancialMemoryType


logger = get_logger(__name__)


# Cues for a goal/preference the user wants remembered.
_GOAL_CUES = (
    "i want", "i'd like", "i would like", "i prefer", "please send me",
    "remind me", "my goal", "i need", "send me", "i like to get",
)

# Cues describing a recurring financial pattern about their customers/payments.
_PATTERN_CUES = (
    "customers usually", "customers often", "customers always", "customers tend",
    "they usually", "they often", "they always", "usually pay late",
    "often pay late", "always pay late", "pay late", "delay payment",
    "delayed payment", "late payment", "inconsistent",
)

# Never persist anything that looks like a credential.
_SECRET_CUES = ("password", "api key", "api-key", "apikey", "token", "secret", "credential")


class MemoryExtractionService:

    def __init__(self, financial_memory_service: FinancialMemoryService):
        self.financial_memory_service = financial_memory_service

    def extract(self, user_id: int, message: str, response: str | None = None) -> list:
        """Store 0..N memories derived from the user's message; return them."""

        text = (message or "").strip()
        lowered = text.lower()

        if not text or self._looks_like_secret(lowered):
            return []

        # Ordinary questions are not memories.
        if self._is_normal_query(lowered):
            return []

        created = []

        if self._matches(lowered, _GOAL_CUES):
            memory = self.financial_memory_service.remember(
                user_id, FinancialMemoryType.USER_GOAL, text, confidence_score=0.8
            )
            if memory is not None:
                created.append(memory)

        if self._matches(lowered, _PATTERN_CUES):
            memory = self.financial_memory_service.remember(
                user_id, FinancialMemoryType.FINANCIAL_PATTERN, text, confidence_score=0.7
            )
            if memory is not None:
                created.append(memory)

        return created

    @staticmethod
    def _matches(text: str, cues) -> bool:
        return any(cue in text for cue in cues)

    @staticmethod
    def _looks_like_secret(text: str) -> bool:
        return any(cue in text for cue in _SECRET_CUES)

    @staticmethod
    def _is_normal_query(text: str) -> bool:
        # A question that isn't expressing a preference/pattern -> not memory.
        if MemoryExtractionService._matches(text, _GOAL_CUES + _PATTERN_CUES):
            return False
        return text.endswith("?") or bool(
            re.match(r"^(how|what|when|who|where|which|does|do|is|are|show|list)\b", text)
        )
