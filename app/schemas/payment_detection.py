from decimal import Decimal

from pydantic import BaseModel, Field
from app.enums.payment_detection import PaymentIntent


class PaymentDetectionResult(BaseModel):

    intent: PaymentIntent

    amount: Decimal | None = Field( default=None, gt=0 )

    currency: str | None = None

    confidence: float = Field( ge=0, le=1 )