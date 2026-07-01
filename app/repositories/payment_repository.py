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
        
    def delete( self, payment: Payment) -> None:
        self.db.delete(payment)
        self.db.commit()
        
    