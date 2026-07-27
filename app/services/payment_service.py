from decimal import Decimal

from app.models.payment import Payment
from app.enums.approval_status import ApprovalStatus
from app.repositories.payment_repository import PaymentRepository


class PaymentService:

    def __init__( self, repository: PaymentRepository ):
        self.repository = repository

    def create_payment( self, payment: Payment ) -> Payment:
        return self.repository.create(payment)

    def get_payment( self, payment_id: int ) -> Payment | None:
        return self.repository.get_by_id(payment_id)

    def get_all_payments( self ) -> list[Payment]:
        return self.repository.get_all()

    def count_pending_approvals( self ) -> int:
        # Only payments that genuinely need a human decision count towards the
        # approval queue -- normal auto-processed payments default to PENDING
        # approval_status but do not require manual review.
        pending = self.repository.get_by_approval_status(ApprovalStatus.PENDING)

        return sum( 1 for payment in pending if payment.requires_manual_review )
    
    def get_contract_payments( self, contract_id: int ) -> list[Payment]:
        return self.repository.get_by_contract_id(contract_id)
    
    def calculate_total_paid( self, contract_id: int) -> Decimal:
        payments = self.get_contract_payments(contract_id)
        
        return sum( ( payment.amount for payment in payments if payment.status == "APPROVED" ), Decimal("0") )
    
    def calculate_remaining_amount( self, total_amount: Decimal, contract_id: int ) -> Decimal:
        total_paid = self.calculate_total_paid(contract_id)
        
        remaining = total_amount - total_paid
        
        return max( remaining, Decimal("0") )