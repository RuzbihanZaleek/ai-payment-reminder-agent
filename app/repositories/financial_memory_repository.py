from sqlalchemy.orm import Session

from app.models.financial_memory import FinancialMemory


class FinancialMemoryRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, memory: FinancialMemory) -> FinancialMemory:
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)

        return memory

    def get_user_memories(self, user_id: int) -> list[FinancialMemory]:
        return (
            self.db.query(FinancialMemory)
            .filter(FinancialMemory.user_id == user_id)
            .order_by(FinancialMemory.created_at.desc())
            .all()
        )

    def get_by_type(self, user_id: int, memory_type: str) -> list[FinancialMemory]:
        return (
            self.db.query(FinancialMemory)
            .filter(FinancialMemory.user_id == user_id)
            .filter(FinancialMemory.memory_type == memory_type)
            .order_by(FinancialMemory.created_at.desc())
            .all()
        )

    def delete(self, memory: FinancialMemory) -> None:
        self.db.delete(memory)
        self.db.commit()
