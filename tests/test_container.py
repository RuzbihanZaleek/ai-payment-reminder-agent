from app.container import create_agent_execution_service
from app.services.agent_execution_service import AgentExecutionService
from app.agents.payment_workflow import PaymentWorkflow
from app.agents.workflow_executor import WorkflowExecutor
from app.repositories.agent_run_repository import AgentRunRepository


class FakeSession:
    """Stand-in for a SQLAlchemy Session; repositories only store it."""
    pass


class FakeLLM:

    def invoke(self, message):

        return None


def _build_service():

    return create_agent_execution_service(
        db=FakeSession(),
        llm=FakeLLM(),
    )


def test_container_creates_agent_execution_service():

    service = _build_service()

    assert isinstance(service, AgentExecutionService)


def test_dependencies_are_wired():

    service = _build_service()

    # Application service -> workflow -> executor
    assert isinstance(service.payment_workflow, PaymentWorkflow)
    assert isinstance(
        service.payment_workflow.workflow_executor,
        WorkflowExecutor,
    )

    # All seven nodes are present on the workflow
    workflow = service.payment_workflow
    assert workflow.payment_detection_node is not None
    assert workflow.confidence_checker_node is not None
    assert workflow.payment_creation_node is not None
    assert workflow.balance_update_node is not None
    assert workflow.reminder_decision_node is not None
    assert workflow.response_generation_node is not None
    assert workflow.notification_node is not None

    # Repositories are wired
    assert isinstance(service.agent_run_repository, AgentRunRepository)
    assert service.payment_workflow.workflow_executor.agent_event_repository is not None


def test_workflow_executor_and_service_share_agent_run_repository():

    service = _build_service()

    executor_repo = service.payment_workflow.workflow_executor.agent_run_repository
    service_repo = service.agent_run_repository

    # Must be the very same instance, not just equal
    assert service_repo is executor_repo
