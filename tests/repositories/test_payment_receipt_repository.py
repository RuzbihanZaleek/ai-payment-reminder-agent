import uuid
from datetime import date
from decimal import Decimal

from app.models.contract import Contract
from app.models.payment import Payment
from app.models.agent_run import AgentRun
from app.models.payment_receipt import PaymentReceipt
from app.enums.agent_run_status import AgentRunStatus
from app.enums.payment_status import PaymentStatus
from app.repositories.contract_repository import ContractRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.payment_receipt_repository import PaymentReceiptRepository


def _seed(db_session):

    contract = ContractRepository(db_session).create(
        Contract(
            reference_code=f"INV-{uuid.uuid4().hex[:12]}",
            name="c",
            total_amount=Decimal("1000"),
            daily_amount=Decimal("10"),
            currency="USD",
            start_date=date.today(),
            whatsapp_chat_id="chat",
        )
    )

    run = AgentRunRepository(db_session).create(
        AgentRun(
            contract_id=contract.id,
            message_id="msg_1",
            status=AgentRunStatus.RUNNING,
        )
    )

    payment = PaymentRepository(db_session).create(
        Payment(
            contract_id=contract.id,
            amount=Decimal("20"),
            payment_date=date.today(),
            status=PaymentStatus.PENDING,
        )
    )

    return run, contract, payment


def _receipt(run, contract, payment):

    return PaymentReceipt(
        agent_run_id=run.id,
        contract_id=contract.id,
        payment_id=payment.id,
        amount=Decimal("20"),
        previous_balance=Decimal("900"),
        new_balance=Decimal("880"),
        allocation_summary="INV001: $20",
    )


def test_create_payment_receipt(db_session):

    run, contract, payment = _seed(db_session)
    repository = PaymentReceiptRepository(db_session)

    created = repository.create(_receipt(run, contract, payment))

    assert created.id is not None
    assert created.previous_balance == Decimal("900")
    assert created.new_balance == Decimal("880")
    assert created.created_at is not None


def test_get_by_payment_id(db_session):

    run, contract, payment = _seed(db_session)
    repository = PaymentReceiptRepository(db_session)

    repository.create(_receipt(run, contract, payment))

    fetched = repository.get_by_payment_id(payment.id)

    assert fetched is not None
    assert fetched.payment_id == payment.id


def test_get_by_agent_run_id(db_session):

    run, contract, payment = _seed(db_session)
    repository = PaymentReceiptRepository(db_session)

    repository.create(_receipt(run, contract, payment))

    receipts = repository.get_by_agent_run_id(run.id)

    assert len(receipts) >= 1
    assert all(r.agent_run_id == run.id for r in receipts)