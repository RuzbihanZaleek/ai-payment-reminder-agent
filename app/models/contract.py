from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import Date, Enum as SqlEnum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, IdMixin

from sqlalchemy.orm import relationship

class ContractStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"

class Contract(Base, IdMixin, TimestampMixin):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    description: Mapped[str | None] = mapped_column(String(500))

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    daily_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="USD",
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[ContractStatus] = mapped_column(
        SqlEnum(ContractStatus),
        default=ContractStatus.ACTIVE,
        nullable=False,
    )

    whatsapp_chat_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    payments = relationship(
        "Payment",
        back_populates="contract",
        cascade="all, delete-orphan",
    )