"""Read-only receipt tool for the assistant.

Delegates to ReceiptReportingService; enforces tenant ownership via
ContractService before returning any contract-scoped receipt data.
"""

from app.enums.sort_order import SortOrder
from app.services.receipt_reporting_service import ReceiptReportingService
from app.services.contract_service import ContractService
from app.ai.tools.ownership import owned_contract


class ReceiptTool:

    def __init__(
        self,
        receipt_reporting_service: ReceiptReportingService,
        contract_service: ContractService,
    ):
        self.receipt_reporting_service = receipt_reporting_service
        self.contract_service = contract_service

    def get_latest_receipts(
        self,
        contract_id: int,
        user_id: int,
        limit: int = 5,
    ) -> list[dict]:
        if owned_contract(self.contract_service, contract_id, user_id) is None:
            return []

        page = self.receipt_reporting_service.get_receipt_history(
            contract_id,
            page=1,
            page_size=limit,
            order=SortOrder.DESC,
        )

        return [
            {
                "receipt_id": r.id,
                "amount": r.amount,
                "previous_balance": r.previous_balance,
                "new_balance": r.new_balance,
                "allocation_summary": r.allocation_summary,
                "created_at": r.created_at,
            }
            for r in page.items
        ]
