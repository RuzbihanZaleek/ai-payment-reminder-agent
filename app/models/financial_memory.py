from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    func,
)

from app.models.base import Base


class FinancialMemory(Base):
    """A durable, user-scoped piece of financial context the assistant remembers.

    Long-term memory (preferences, goals, observed patterns, risk signals) that
    persists across conversations. Strictly per-user -- never read across
    tenants. Never store secrets/credentials here.
    """

    __tablename__ = "financial_memories"

    id = Column( Integer, primary_key=True )

    user_id = Column( Integer, ForeignKey("users.id"), nullable=False, index=True )

    # Stores a FinancialMemoryType value.
    memory_type = Column( String(50), nullable=False, index=True )

    content = Column( Text, nullable=False )

    confidence_score = Column( Float, nullable=False, server_default="1.0" )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
