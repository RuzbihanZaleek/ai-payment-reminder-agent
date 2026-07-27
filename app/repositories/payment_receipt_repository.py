from sqlalchemy.orm import Session

from app.models.payment_receipt import PaymentReceipt


class PaymentReceiptRepository:

    def __init__( self, db: Session):
        self.db = db

    def create( self, payment_receipt: PaymentReceipt ) -> PaymentReceipt:
        self.db.add(payment_receipt)
        self.db.commit()
        self.db.refresh(payment_receipt)

        return payment_receipt

    def get_by_payment_id( self, payment_id: int ) -> PaymentReceipt | None:
        return (
            self.db.query(PaymentReceipt)
            .filter(PaymentReceipt.payment_id == payment_id)
            .first()
        )

    def get_by_agent_run_id( self, agent_run_id: int ) -> list[PaymentReceipt]:
        return (
            self.db.query(PaymentReceipt)
            .filter(PaymentReceipt.agent_run_id == agent_run_id)
            .all()
        )