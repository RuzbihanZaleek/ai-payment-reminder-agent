from app.enums.agent_run_status import AgentRunStatus
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_event_repository import AgentEventRepository
from app.repositories.filters import AgentRunFilter
from app.repositories.pagination import PageResult
from app.enums.sort_order import SortOrder


class AgentReportingService:

    def __init__(
        self,
        agent_run_repository: AgentRunRepository,
        agent_event_repository: AgentEventRepository,
    ):
        self.agent_run_repository = agent_run_repository
        self.agent_event_repository = agent_event_repository

    def get_recent_runs(
        self,
        user_id: int,
        run_filter: AgentRunFilter,
        page: int,
        page_size: int,
        order: SortOrder,
    ) -> PageResult:

        return self.agent_run_repository.get_for_user_page(
            user_id,
            run_filter,
            page,
            page_size,
            order,
        )

    def get_run_details(self, run_id: int, user_id: int) -> dict | None:

        run = self.agent_run_repository.get_by_id_for_user(run_id, user_id)

        if run is None:
            return None

        return {
            "run": run,
            "events": self.agent_event_repository.get_by_run_id(run_id),
        }

    def get_agent_stats(self, user_id: int) -> dict:

        runs = self.agent_run_repository.get_all_for_user(user_id)

        return {
            "total_agent_runs": len(runs),
            "completed_runs": sum(
                1 for r in runs if r.status == AgentRunStatus.COMPLETED
            ),
            "failed_runs": sum(
                1 for r in runs if r.status == AgentRunStatus.FAILED
            ),
        }