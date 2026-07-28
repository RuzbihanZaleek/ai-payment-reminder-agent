"""Long-term financial memory (store / retrieve).

Persists user-scoped financial context (preferences, goals, observed patterns,
risk signals) so the advisor can personalize across conversations. Strictly
per-user; never stores secrets/credentials (the extraction layer decides *what*
is worth remembering, this layer just persists it).
"""

from app.core.logger import get_logger
from app.models.financial_memory import FinancialMemory
from app.repositories.financial_memory_repository import FinancialMemoryRepository
from app.services.ai_memory.memory_types import FinancialMemoryType


logger = get_logger(__name__)

# Cap how many memories are surfaced into an LLM prompt.
_RELEVANT_LIMIT = 10


class FinancialMemoryService:

    def __init__(self, repository: FinancialMemoryRepository, audit_service=None):
        self.repository = repository
        self.audit_service = audit_service

    def remember(
        self,
        user_id: int,
        memory_type: FinancialMemoryType,
        content: str,
        confidence_score: float = 1.0,
    ) -> FinancialMemory | None:
        """Persist a memory, skipping exact duplicates for the user."""

        type_value = (
            memory_type.value if hasattr(memory_type, "value") else memory_type
        )

        # De-duplicate: don't store the same content twice for a user.
        existing = self.repository.get_user_memories(user_id)
        if any(m.content == content and m.memory_type == type_value for m in existing):
            return None

        memory = self.repository.create(
            FinancialMemory(
                user_id=user_id,
                memory_type=type_value,
                content=content,
                confidence_score=confidence_score,
            )
        )

        logger.info(
            "ai_memory_created",
            extra={"user_id": user_id, "memory_type": type_value},
        )

        if self.audit_service is not None:
            self.audit_service.record(
                action=self.audit_service.AI_MEMORY_CREATED,
                user_id=user_id,
                entity_type="financial_memory",
                entity_id=memory.id,
                metadata={"memory_type": type_value, "confidence_score": confidence_score},
            )

        return memory

    def get_user_memories(self, user_id: int) -> list[FinancialMemory]:
        return self.repository.get_user_memories(user_id)

    def get_by_type(self, user_id: int, memory_type: FinancialMemoryType) -> list[FinancialMemory]:
        type_value = (
            memory_type.value if hasattr(memory_type, "value") else memory_type
        )
        return self.repository.get_by_type(user_id, type_value)

    def get_relevant_memories(self, user_id: int, limit: int = _RELEVANT_LIMIT) -> list[dict]:
        """A compact, LLM-friendly view of the user's most recent memories."""

        memories = self.repository.get_user_memories(user_id)[:limit]
        return [
            {"type": m.memory_type, "content": m.content}
            for m in memories
        ]

    def delete(self, memory: FinancialMemory) -> None:
        self.repository.delete(memory)
