from app.services.contract_analytics_service import ContractAnalyticsService
from app.services.payment_analytics_service import PaymentAnalyticsService
from app.services.reminder_analytics_service import ReminderAnalyticsService
from app.services.agent_analytics_service import AgentAnalyticsService


class AnalyticsService:
    """Composes the per-domain analytics services into a single overview.

    Contains no calculation logic -- each section is produced by the
    corresponding analytics service.
    """

    def __init__(
        self,
        contract_analytics_service: ContractAnalyticsService,
        payment_analytics_service: PaymentAnalyticsService,
        reminder_analytics_service: ReminderAnalyticsService,
        agent_analytics_service: AgentAnalyticsService,
    ):
        self.contract_analytics_service = contract_analytics_service
        self.payment_analytics_service = payment_analytics_service
        self.reminder_analytics_service = reminder_analytics_service
        self.agent_analytics_service = agent_analytics_service

    def get_overview(self) -> dict:

        return {
            "contracts": self.contract_analytics_service.get_contract_analytics(),
            "payments": self.payment_analytics_service.get_payment_analytics(),
            "reminders": self.reminder_analytics_service.get_reminder_analytics(),
            "agents": self.agent_analytics_service.get_agent_analytics(),
        }