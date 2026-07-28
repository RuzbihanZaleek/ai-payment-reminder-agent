"""Read-only contract tool for the assistant.

Delegates to existing domain/reporting services (never repositories). All access
is tenant-scoped by ``user_id``.
"""

from app.models.contract import ContractStatus
from app.services.contract_service import ContractService
from app.services.contract_reporting_service import ContractReportingService


class ContractTool:

    def __init__(
        self,
        contract_service: ContractService,
        contract_reporting_service: ContractReportingService,
    ):
        self.contract_service = contract_service
        self.contract_reporting_service = contract_reporting_service

    def get_active_contracts(self, user_id: int) -> list[dict]:
        contracts = self.contract_service.get_user_contracts(
            user_id, ContractStatus.ACTIVE
        )

        return [
            {
                "contract_id": c.id,
                "reference_code": c.reference_code,
                "name": c.name,
                "total_amount": c.total_amount,
                "daily_amount": c.daily_amount,
                "currency": c.currency,
                "status": c.status.value if hasattr(c.status, "value") else c.status,
            }
            for c in contracts
        ]

    def get_contract_summary(self, contract_id: int, user_id: int) -> dict | None:
        # Reporting service is already tenant-scoped (returns None if not owned).
        return self.contract_reporting_service.get_contract_summary(
            contract_id, user_id
        )
