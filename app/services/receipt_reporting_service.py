from app.repositories.payment_receipt_repository import PaymentReceiptRepository
from app.repositories.pagination import PageResult
from app.enums.sort_order import SortOrder


class ReceiptReportingService:

    def __init__(
        self,
        payment_receipt_repository: PaymentReceiptRepository,
    ):
        self.payment_receipt_repository = payment_receipt_repository

    def get_receipt_history(
        self,
        contract_id: int,
        page: int,
        page_size: int,
        order: SortOrder,
    ) -> PageResult:

        return self.payment_receipt_repository.get_by_contract_id_page(
            contract_id,
            page,
            page_size,
            order,
        )