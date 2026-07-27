from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    Text,
    DateTime,
    ForeignKey,
    func,
)

from app.models.base import Base


class PaymentReceipt(Base):

    __tablename__ = "payment_receipts"

    id = Column( Integer, primary_key=True )

    agent_run_id = Column( Integer, ForeignKey("agent_runs.id"), nullable=False )

    contract_id = Column( Integer, ForeignKey("contracts.id"), nullable=False )

    payment_id = Column( Integer, ForeignKey("payments.id"), nullable=False )

    amount = Column( Numeric(10, 2), nullable=False )

    previous_balance = Column( Numeric(10, 2), nullable=False )

    new_balance = Column( Numeric(10, 2), nullable=False )

    allocation_summary = Column( Text, nullable=True )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )