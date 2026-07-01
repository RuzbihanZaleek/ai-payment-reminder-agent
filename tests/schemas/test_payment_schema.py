from datetime import date, timedelta, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
)
from app.enums.payment_status import PaymentStatus
from app.enums.payment_source import PaymentSource


def test_create_payment_with_valid_data():
    payment = PaymentCreate(
        contract_id=1,
        amount=Decimal("20.00"),
        payment_date=date.today(),
        source=PaymentSource.WHATSAPP_AI
    )

    assert payment.contract_id == 1
    assert payment.amount == Decimal("20.00")
    assert payment.source == PaymentSource.WHATSAPP_AI


def test_payment_amount_cannot_be_zero():

    with pytest.raises(ValidationError):
        PaymentCreate(
            contract_id=1,
            amount=Decimal("0"),
            payment_date=date.today(),
            source=PaymentSource.MANUAL
        )


def test_payment_amount_cannot_be_negative():

    with pytest.raises(ValidationError):
        PaymentCreate(
            contract_id=1,
            amount=Decimal("-10"),
            payment_date=date.today(),
            source=PaymentSource.MANUAL
        )


def test_payment_date_cannot_be_in_future():

    future_date = date.today() + timedelta(days=1)

    with pytest.raises(ValidationError):
        PaymentCreate(
            contract_id=1,
            amount=Decimal("20"),
            payment_date=future_date,
            source=PaymentSource.MANUAL
        )


def test_invalid_payment_source_rejected():

    with pytest.raises(ValidationError):
        PaymentCreate(
            contract_id=1,
            amount=Decimal("20"),
            payment_date=date.today(),
            source="INVALID_SOURCE"
        )


def test_payment_update_accepts_partial_data():

    update = PaymentUpdate(
        status=PaymentStatus.APPROVED
    )

    assert update.status == PaymentStatus.APPROVED


def test_payment_update_can_accept_notes_only():

    update = PaymentUpdate(
        notes="Payment verified from WhatsApp message"
    )

    assert update.notes == "Payment verified from WhatsApp message"


def test_payment_response_from_attributes():

    class FakePayment:
        id = 1
        contract_id = 1
        amount = Decimal("20.00")
        payment_date = date.today()
        status = PaymentStatus.APPROVED
        source = PaymentSource.WHATSAPP_AI
        reference_message_id = "msg_123"
        notes = "Paid through WhatsApp"
        approved_at = None
        approved_by = "user"
        created_at = datetime.now()
        updated_at = datetime.now()

    response = PaymentResponse.model_validate(
        FakePayment()
    )

    assert response.id == 1
    assert response.amount == Decimal("20.00")
    assert response.source == PaymentSource.WHATSAPP_AI