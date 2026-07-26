from app.db.session import SessionLocal

from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_event_repository import AgentEventRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.contract_repository import ContractRepository

from app.services.payment_service import PaymentService
from app.services.contract_service import ContractService
from app.services.notification_service import NotificationService
from app.services.agent_execution_service import AgentExecutionService

from app.agents.payment_message_agent import PaymentMessageAgent
from app.agents.confidence_checker import ConfidenceChecker

from app.agents.payment_detection_node import PaymentDetectionNode
from app.agents.confidence_checker_node import ConfidenceCheckerNode
from app.agents.payment_creation_node import PaymentCreationNode
from app.agents.balance_update_node import BalanceUpdateNode
from app.agents.reminder_decision_node import ReminderDecisionNode
from app.agents.response_generation_node import ResponseGenerationNode
from app.agents.notification_node import NotificationNode

from app.agents.workflow_executor import WorkflowExecutor
from app.agents.payment_workflow import PaymentWorkflow


def create_agent_execution_service(
    db=None,
    llm=None,
) -> AgentExecutionService:
    """Compose the full agent execution stack and return the entry-point service.

    ``db`` and ``llm`` default to the real session/LLM, but can be injected
    (e.g. in tests) to avoid a live database or API key.
    """

    if db is None:
        db = SessionLocal()

    # Repositories -- all share the same session.
    agent_run_repository = AgentRunRepository(db)
    agent_event_repository = AgentEventRepository(db)
    payment_repository = PaymentRepository(db)
    contract_repository = ContractRepository(db)

    # Services.
    payment_service = PaymentService(payment_repository)
    contract_service = ContractService(contract_repository)
    notification_service = NotificationService()

    # Agents.
    if llm is None:
        # Imported lazily so tests injecting a fake llm don't pull in langchain.
        from app.llm.client import OpenAIClient

        llm = OpenAIClient()

    payment_agent = PaymentMessageAgent(llm)
    confidence_checker = ConfidenceChecker()

    # Nodes.
    payment_detection_node = PaymentDetectionNode(payment_agent)
    confidence_checker_node = ConfidenceCheckerNode(confidence_checker)
    payment_creation_node = PaymentCreationNode(payment_service)
    balance_update_node = BalanceUpdateNode(payment_service, contract_service)
    reminder_decision_node = ReminderDecisionNode()
    response_generation_node = ResponseGenerationNode()
    notification_node = NotificationNode(notification_service)

    # Infrastructure -- receives the shared AgentRunRepository.
    workflow_executor = WorkflowExecutor(
        agent_run_repository,
        agent_event_repository,
    )

    # Workflow.
    payment_workflow = PaymentWorkflow(
        payment_detection_node,
        confidence_checker_node,
        payment_creation_node,
        balance_update_node,
        reminder_decision_node,
        response_generation_node,
        notification_node,
        workflow_executor,
    )

    # Application service -- receives the same shared AgentRunRepository.
    return AgentExecutionService(
        agent_run_repository,
        payment_workflow,
    )
