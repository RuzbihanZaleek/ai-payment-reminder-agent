from app.models.agent_run import AgentRun
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_event_repository import AgentEventRepository


class AgentReportingService:

    def __init__(
        self,
        agent_run_repository: AgentRunRepository,
        agent_event_repository: AgentEventRepository,
    ):
        self.agent_run_repository = agent_run_repository
        self.agent_event_repository = agent_event_repository

    def get_recent_runs(self, limit: int = 20) -> list[AgentRun]:

        return self.agent_run_repository.get_recent(limit)

    def get_run_details(self, run_id: int) -> dict | None:

        run = self.agent_run_repository.get_by_id(run_id)

        if run is None:
            return None

        return {
            "run": run,
            "events": self.agent_event_repository.get_by_run_id(run_id),
        }