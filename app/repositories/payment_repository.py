from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.repositories.filters import PaymentFilter
from app.repositories.pagination import PageResult, apply_ordering, paginate
from app.enums.sort_order import SortOrder


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

    def _apply_payment_filters( self, query, payment_filter: PaymentFilter ):
        if payment_filter.status is not None:
            query = query.filter(Payment.status == payment_filter.status)

        if payment_filter.approval_status is not None:
            query = query.filter(
                Payment.approval_status == payment_filter.approval_status
            )

        if payment_filter.date_from is not None:
            query = query.filter(Payment.payment_date >= payment_filter.date_from)

        if payment_filter.date_to is not None:
            query = query.filter(Payment.payment_date <= payment_filter.date_to)

        if payment_filter.min_amount is not None:
            query = query.filter(Payment.amount >= payment_filter.min_amount)

        if payment_filter.max_amount is not None:
            query = query.filter(Payment.amount <= payment_filter.max_amount)

        return query

    def get_by_contract_id_page(
        self,
        contract_id: int,
        payment_filter: PaymentFilter,
        page: int,
        page_size: int,
        order: SortOrder,
    ) -> PageResult:
        query = (
            self.db.query(Payment)
            .filter(Payment.contract_id == contract_id)
        )
        query = self._apply_payment_filters(query, payment_filter)
        query = apply_ordering(query, Payment.id, order)

        return paginate(query, page, page_size)

    def get_by_approval_status_for_user_page(
        self,
        user_id: int,
        approval_status,
        page: int,
        page_size: int,
        order: SortOrder,
    ) -> PageResult:
        from app.models.contract import Contract

        query = (
            self.db.query(Payment)
            .join(Contract, Payment.contract_id == Contract.id)
            .filter(Contract.user_id == user_id)
            .filter(Payment.approval_status == approval_status)
        )
        query = apply_ordering(query, Payment.id, order)

        return paginate(query, page, page_size)

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
        
    