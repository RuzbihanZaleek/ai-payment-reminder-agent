from app.services.agent_reporting_service import AgentReportingService


class AgentAnalyticsService:

    def __init__(
        self,
        agent_reporting_service: AgentReportingService,
    ):
        self.agent_reporting_service = agent_reporting_service

    def get_agent_analytics(self, user_id: int) -> dict:

        stats = self.agent_reporting_service.get_agent_stats(user_id)

        total = stats["total_agent_runs"]
        completed = stats["completed_runs"]

        success_rate = float(completed / total) if total else 0.0

        return {
            "total_agent_runs": total,
            "completed_runs": completed,
            "failed_runs": stats["failed_runs"],
            "success_rate": round(success_rate, 4),
        }