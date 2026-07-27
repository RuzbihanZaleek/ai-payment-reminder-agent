from app.models.payment_receipt import PaymentReceipt
from app.repositories.payment_receipt_repository import PaymentReceiptRepository


class ReceiptReportingService:

    def __init__(
        self,
        payment_receipt_repository: PaymentReceiptRepository,
    ):
        self.payment_receipt_repository = payment_receipt_repository

    def get_receipt_history(self, contract_id: int) -> list[PaymentReceipt]:

        return self.payment_receipt_repository.get_by_contract_id(contract_id)