from enum import Enum
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator, ConfigDict

class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    LKR = "LKR"


class ContractCreate(BaseModel):
    name: str = Field(
        min_length=3,
        max_length=100
    )

    description: str | None = Field(
        default=None,
        max_length=500
    )

    total_amount: Decimal = Field(
        gt=0
    )

    daily_amount: Decimal = Field(
        gt=0
    )

    currency: Currency = Currency.USD

    start_date: date

    end_date: date | None = None

    whatsapp_chat_id: str = Field(
        min_length=1,
        max_length=255
    )
    
    @model_validator(mode="after")
    def validate_contract(self):

        if self.daily_amount > self.total_amount:
            raise ValueError(
                "Daily amount cannot be greater than total amount"
            )

        if self.start_date > date.today():
            raise ValueError(
                "Start date cannot be in the future"
            )

        if self.end_date and self.end_date <= self.start_date:
            raise ValueError(
                "End date must be after start date"
            )

        return self
    
class ContractUpdate(BaseModel):

    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=100
    )

    description: str | None = None

    daily_amount: Decimal | None = Field(
        default=None,
        gt=0
    )

    status: str | None = None

    end_date: date | None = None
    
class ContractResponse(BaseModel):

    id: int

    name: str

    description: str | None

    total_amount: Decimal

    daily_amount: Decimal

    currency: Currency

    start_date: date

    end_date: date | None

    status: str

    whatsapp_chat_id: str

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )