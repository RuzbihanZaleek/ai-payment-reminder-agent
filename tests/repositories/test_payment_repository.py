from datetime import date
from decimal import Decimal

from app.models.payment import Payment
from app.enums.payment_status import PaymentStatus
from app.enums.payment_source import PaymentSource
from app.repositories.payment_repository import PaymentRepository


def test_create_payment(db_session):

    repository = PaymentRepository(db_session)

    payment = Payment(
        contract_id=1,
        amount=Decimal("20.00"),
        payment_date=date.today(),
        status=PaymentStatus.PENDING,
        source=PaymentSource.MANUAL
    )

    created_payment = repository.create(payment)

    assert created_payment.id is not None
    assert created_payment.amount == Decimal("20.00")


def test_get_payment_by_id(db_session):

    repository = PaymentRepository(db_session)

    payment = Payment(
        contract_id=1,
        amount=Decimal("30.00"),
        payment_date=date.today(),
        status=PaymentStatus.APPROVED,
        source=PaymentSource.WHATSAPP_AI
    )

    created_payment = repository.create(payment)

    fetched_payment = repository.get_by_id(
        created_payment.id
    )

    assert fetched_payment is not None
    assert fetched_payment.id == created_payment.id
    assert fetched_payment.status == PaymentStatus.APPROVED


def test_get_payments_by_contract_id(db_session):

    repository = PaymentRepository(db_session)

    payment1 = Payment(
        contract_id=1,
        amount=Decimal("20.00"),
        payment_date=date.today(),
        status=PaymentStatus.APPROVED,
        source=PaymentSource.WHATSAPP_AI
    )

    payment2 = Payment(
        contract_id=1,
        amount=Decimal("30.00"),
        payment_date=date.today(),
        status=PaymentStatus.APPROVED,
        source=PaymentSource.MANUAL
    )

    repository.create(payment1)
    repository.create(payment2)

    payments = repository.get_by_contract_id(
        1
    )

    assert len(payments) >= 2


def test_delete_payment(db_session):

    repository = PaymentRepository(db_session)

    payment = Payment(
        contract_id=1,
        amount=Decimal("50.00"),
        payment_date=date.today(),
        status=PaymentStatus.PENDING,
        source=PaymentSource.MANUAL
    )

    created_payment = repository.create(payment)

    repository.delete(created_payment)

    deleted_payment = repository.get_by_id(
        created_payment.id
    )

    assert deleted_payment is None