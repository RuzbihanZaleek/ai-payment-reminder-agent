from sqlalchemy.orm import Session

from app.models.payment import Payment


class PaymentRepository:

    def __init__( self, db: Session):
        self.db = db
        
    def create( self, payment: Payment ) -> Payment:
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)

        return payment

    def get_all( self ) -> list[Payment]:
        return (
            self.db.query(Payment)
            .all()
        )

    def get_all_for_user( self, user_id: int ) -> list[Payment]:
        from app.models.contract import Contract

        return (
            self.db.query(Payment)
            .join(Contract, Payment.contract_id == Contract.id)
            .filter(Contract.user_id == user_id)
            .all()
        )

    def get_by_id( self, payment_id: int) -> Payment | None:
        return (
            self.db.query(Payment)
            .filter(Payment.id == payment_id)
            .first()
        )
        
    def get_by_contract_id( self, contract_id: int) -> list[Payment]:
        return (
            self.db.query(Payment)
            .filter(Payment.contract_id == contract_id)
            .all()
        )

    def get_by_approval_status( self, approval_status ) -> list[Payment]:
        return (
            self.db.query(Payment)
            .filter(Payment.approval_status == approval_status)
            .all()
        )

    def has_payment_for_date( self, contract_id: int, payment_date ) -> bool:
        return (
            self.db.query(Payment)
            .filter(Payment.contract_id == contract_id)
            .filter(Payment.payment_date == payment_date)
            .first()
            is not None
        )

    def update( self, payment: Payment ) -> Payment:
        self.db.commit()
        self.db.refresh(payment)

        return payment

    def delete( self, payment: Payment) -> None:
        self.db.delete(payment)
        self.db.commit()
        
    