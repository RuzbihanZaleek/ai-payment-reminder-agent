from decimal import Decimal
from unittest.mock import Mock

from app.models.payment import Payment
from app.services.payment_service import PaymentService
from app.enums.payment_status import PaymentStatus
from app.enums.payment_source import PaymentSource


def test_create_payment():

    repository = Mock()

    payment = Payment(
        id=1,
        contract_id=1,
        amount=Decimal("20.00"),
        status=PaymentStatus.APPROVED,
        source=PaymentSource.MANUAL
    )

    repository.create.return_value = payment

    service = PaymentService(repository)

    result = service.create_payment(payment)

    assert result == payment
    repository.create.assert_called_once_with(payment)


def test_get_payment():

    repository = Mock()

    payment = Payment(
        id=1,
        contract_id=1,
        amount=Decimal("50.00")
    )

    repository.get_by_id.return_value = payment

    service = PaymentService(repository)

    result = service.get_payment(1)

    assert result == payment
    repository.get_by_id.assert_called_once_with(1)


def test_get_contract_payments():

    repository = Mock()

    payments = [
        Payment(
            contract_id=1,
            amount=Decimal("20.00")
        ),
        Payment(
            contract_id=1,
            amount=Decimal("30.00")
        )
    ]

    repository.get_by_contract_id.return_value = payments

    service = PaymentService(repository)

    result = service.get_contract_payments(1)

    assert len(result) == 2
    repository.get_by_contract_id.assert_called_once_with(1)


def test_calculate_total_paid_only_counts_approved_payments():

    repository = Mock()

    payments = [
        Payment(
            contract_id=1,
            amount=Decimal("100.00"),
            status=PaymentStatus.APPROVED
        ),
        Payment(
            contract_id=1,
            amount=Decimal("50.00"),
            status=PaymentStatus.PENDING
        ),
        Payment(
            contract_id=1,
            amount=Decimal("20.00"),
            status=PaymentStatus.APPROVED
        ),
    ]

    repository.get_by_contract_id.return_value = payments

    service = PaymentService(repository)

    total_paid = service.calculate_total_paid(1)

    assert total_paid == Decimal("120.00")


def test_calculate_remaining_amount():

    repository = Mock()

    payments = [
        Payment(
            contract_id=1,
            amount=Decimal("900.00"),
            status=PaymentStatus.APPROVED
        ),
        Payment(
            contract_id=1,
            amount=Decimal("100.00"),
            status=PaymentStatus.APPROVED
        ),
    ]

    repository.get_by_contract_id.return_value = payments

    service = PaymentService(repository)

    remaining = service.calculate_remaining_amount(
        Decimal("2200.00"),
        1
    )

    assert remaining == Decimal("1200.00")


def test_remaining_amount_cannot_be_negative():

    repository = Mock()

    payments = [
        Payment(
            contract_id=1,
            amount=Decimal("2500.00"),
            status=PaymentStatus.APPROVED
        )
    ]

    repository.get_by_contract_id.return_value = payments

    service = PaymentService(repository)

    remaining = service.calculate_remaining_amount(
        Decimal("2200.00"),
        1
    )

    assert remaining == Decimal("0")