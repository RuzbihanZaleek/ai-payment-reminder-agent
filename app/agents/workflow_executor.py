from datetime import datetime, timezone

from app.agents.state import AgentState
from app.models.agent_event import AgentEvent
from app.enums.agent_event_status import AgentEventStatus
from app.enums.agent_run_status import AgentRunStatus
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_event_repository import AgentEventRepository


class WorkflowExecutor:

    def __init__(
        self,
        agent_run_repository: AgentRunRepository,
        agent_event_repository: AgentEventRepository,
    ):
        self.agent_run_repository = agent_run_repository
        self.agent_event_repository = agent_event_repository

    def execute_node(
        self,
        agent_run_id: int,
        node_name: str,
        node,
        state: AgentState,
    ) -> AgentState:

        self._record_event(
            agent_run_id,
            node_name,
            AgentEventStatus.STARTED,
        )

        try:
            state = node.execute(state)
        except Exception as exc:
            self._record_event(
                agent_run_id,
                node_name,
                AgentEventStatus.FAILED,
                message=str(exc),
            )
            self.mark_run_failed(agent_run_id)
            raise

        self._record_event(
            agent_run_id,
            node_name,
            AgentEventStatus.COMPLETED,
        )

        return state

    def mark_run_completed(
        self,
        agent_run_id: int,
    ):

        return self._set_run_status(
            agent_run_id,
            AgentRunStatus.COMPLETED,
        )

    def mark_run_failed(
        self,
        agent_run_id: int,
    ):

        return self._set_run_status(
            agent_run_id,
            AgentRunStatus.FAILED,
        )

    def _record_event(
        self,
        agent_run_id: int,
        node_name: str,
        status: AgentEventStatus,
        message: str | None = None,
    ) -> AgentEvent:

        event = AgentEvent(
            agent_run_id=agent_run_id,
            node_name=node_name,
            status=status,
            message=message,
        )

        return self.agent_event_repository.create(event)

    def _set_run_status(
        self,
        agent_run_id: int,
        status: AgentRunStatus,
    ):

        run = self.agent_run_repository.get_by_id(agent_run_id)

        if run is None:
            return None

        run.status = status
        run.completed_at = datetime.now(timezone.utc)

        return self.agent_run_repository.update(run)
