from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.payment_detection import PaymentDetectionResult
from app.enums.payment_detection import PaymentIntent


def test_payment_detection_schema_success():

    result = PaymentDetectionResult(
        intent=PaymentIntent.PAYMENT_RECEIVED,
        amount=Decimal("100"),
        currency="USD",
        confidence=0.95
    )

    assert result.amount == Decimal("100")
    assert result.intent == PaymentIntent.PAYMENT_RECEIVED


def test_payment_detection_invalid_amount():

    with pytest.raises(ValidationError):

        PaymentDetectionResult(
            intent=PaymentIntent.PAYMENT_RECEIVED,
            amount=Decimal("-10"),
            confidence=0.9
        )


def test_payment_detection_invalid_confidence():

    with pytest.raises(ValidationError):

        PaymentDetectionResult(
            intent=PaymentIntent.PAYMENT_RECEIVED,
            amount=Decimal("100"),
            confidence=2
        )