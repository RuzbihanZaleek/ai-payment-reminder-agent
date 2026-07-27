from app.services.contract_reporting_service import ContractReportingService
from app.services.payment_reporting_service import PaymentReportingService
from app.services.agent_reporting_service import AgentReportingService
from app.services.scheduler_reporting_service import SchedulerReportingService


class DashboardService:
    """Aggregates dashboard stats by composing the existing reporting services.

    Contains no calculation logic of its own -- each section is produced by the
    corresponding reporting service.
    """

    def __init__(
        self,
        contract_reporting_service: ContractReportingService,
        payment_reporting_service: PaymentReportingService,
        agent_reporting_service: AgentReportingService,
        scheduler_reporting_service: SchedulerReportingService,
    ):
        self.contract_reporting_service = contract_reporting_service
        self.payment_reporting_service = payment_reporting_service
        self.agent_reporting_service = agent_reporting_service
        self.scheduler_reporting_service = scheduler_reporting_service

    def get_overview(self) -> dict:

        return {
            "contracts": self.contract_reporting_service.get_contract_stats(),
            "payments": self.payment_reporting_service.get_payment_stats(),
            "agents": self.agent_reporting_service.get_agent_stats(),
            "scheduler": self.scheduler_reporting_service.get_scheduler_stats(),
        }