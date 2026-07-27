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

    def get_user_payments( self, user_id: int ) -> list[Payment]:
        return self.repository.get_all_for_user(user_id)

    # --- Single-source business rules (applied to any payment list) ---------

    @staticmethod
    def _approved( payments: list[Payment] ) -> list[Payment]:
        # Confirmed money: APPROVED approval_status only.
        return [p for p in payments if p.approval_status == ApprovalStatus.APPROVED]

    @staticmethod
    def _pending_reviews( payments: list[Payment] ) -> list[Payment]:
        # Genuinely awaiting a human decision.
        return [
            p for p in payments
            if p.requires_manual_review
            and p.approval_status == ApprovalStatus.PENDING
        ]

    @staticmethod
    def _sum( payments: list[Payment] ) -> Decimal:
        return sum( ( p.amount for p in payments ), Decimal("0") )

    # --- Global stats -------------------------------------------------------

    def count_pending_approvals( self ) -> int:
        return len(self._pending_reviews(
            self.repository.get_by_approval_status(ApprovalStatus.PENDING)
        ))

    def calculate_pending_review_amount( self ) -> Decimal:
        return self._sum(self._pending_reviews(
            self.repository.get_by_approval_status(ApprovalStatus.PENDING)
        ))

    def calculate_total_received( self ) -> Decimal:
        return self._sum(
            self.repository.get_by_approval_status(ApprovalStatus.APPROVED)
        )

    # --- User-scoped stats (tenant isolation) -------------------------------

    def count_pending_reviews_for_user( self, user_id: int ) -> int:
        return len(self._pending_reviews(self.get_user_payments(user_id)))

    def calculate_pending_review_amount_for_user( self, user_id: int ) -> Decimal:
        return self._sum(self._pending_reviews(self.get_user_payments(user_id)))

    def calculate_total_received_for_user( self, user_id: int ) -> Decimal:
        return self._sum(self._approved(self.get_user_payments(user_id)))
    
    def get_contract_payments( self, contract_id: int ) -> list[Payment]:
        return self.repository.get_by_contract_id(contract_id)
    
    def calculate_total_paid( self, contract_id: int) -> Decimal:
        payments = self.get_contract_payments(contract_id)
        
        return sum( ( payment.amount for payment in payments if payment.status == "APPROVED" ), Decimal("0") )
    
    def calculate_remaining_amount( self, total_amount: Decimal, contract_id: int ) -> Decimal:
        total_paid = self.calculate_total_paid(contract_id)
        
        remaining = total_amount - total_paid
        
        return max( remaining, Decimal("0") )