import time
from datetime import datetime, timezone

from app.agents.state import AgentState
from app.agents.payment_workflow import PaymentWorkflow
from app.core.metrics import record_workflow
from app.models.agent_run import AgentRun
from app.enums.agent_run_status import AgentRunStatus
from app.repositories.agent_run_repository import AgentRunRepository


class AgentExecutionService:

    def __init__(
        self,
        agent_run_repository: AgentRunRepository,
        payment_workflow: PaymentWorkflow,
    ):
        self.agent_run_repository = agent_run_repository
        self.payment_workflow = payment_workflow

    def execute(
        self,
        contract_id: int,
        message_id: str,
        message: str,
        conversation_id: int | None = None,
        conversation_history: list | None = None,
        resolved_contracts: list | None = None,
    ) -> AgentState:

        agent_run = AgentRun(
            contract_id=contract_id,
            message_id=message_id,
            status=AgentRunStatus.PENDING,
        )

        agent_run = self.agent_run_repository.create(agent_run)

        agent_run.status = AgentRunStatus.RUNNING
        self.agent_run_repository.update(agent_run)

        state = AgentState(
            message=message,
            message_id=message_id,
            contract_id=contract_id,
            agent_run_id=agent_run.id,
            pending_dates=[],
            requires_approval=False,
            conversation_id=conversation_id,
            conversation_history=conversation_history or [],
            resolved_contracts=resolved_contracts or [],
        )

        start = time.perf_counter()
        try:
            # The workflow marks the run COMPLETED after its final node.
            result = self.payment_workflow.process(state, agent_run.id)
            record_workflow(success=True, duration_seconds=time.perf_counter() - start)
            return result
        except Exception:
            # A failure may surface before the workflow marks the run failed
            # (or from a workflow that never got that far), so guarantee it here.
            record_workflow(success=False, duration_seconds=time.perf_counter() - start)
            agent_run.status = AgentRunStatus.FAILED
            agent_run.completed_at = datetime.now(timezone.utc)
            self.agent_run_repository.update(agent_run)
            raise
