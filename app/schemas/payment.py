from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.enums.payment_status import PaymentStatus
from app.enums.payment_source import PaymentSource


class PaymentCreate(BaseModel):

    contract_id: int

    amount: Decimal = Field(
        gt=0
    )

    payment_date: date

    source: PaymentSource = PaymentSource.MANUAL

    reference_message_id: str | None = Field(
        default=None,
        max_length=255
    )

    notes: str | None = Field(
        default=None,
        max_length=500
    )
    
    @field_validator("payment_date")
    @classmethod
    def validate_payment_date(cls, value: date):

        if value > date.today():
            raise ValueError(
                "Payment date cannot be in the future"
            )

        return value


class PaymentUpdate(BaseModel):

    status: PaymentStatus | None = None

    notes: str | None = Field(
        default=None,
        max_length=500
    )

    approved_by: str | None = Field(
        default=None,
        max_length=100
    )


class PaymentResponse(BaseModel):

    id: int

    contract_id: int

    amount: Decimal

    payment_date: date

    status: PaymentStatus

    source: PaymentSource

    reference_message_id: str | None

    notes: str | None

    approved_at: datetime | None

    approved_by: str | None

    created_at: datetime

    updated_at: datetime


    model_config = ConfigDict(
        from_attributes=True
    )