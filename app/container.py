from app.db.session import SessionLocal

from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_event_repository import AgentEventRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.contract_repository import ContractRepository

from app.core.config import settings

from app.services.payment_service import PaymentService
from app.services.contract_service import ContractService
from app.services.whatsapp_notification_service import WhatsAppNotificationService
from app.services.payment_approval_service import PaymentApprovalService
from app.services.agent_execution_service import AgentExecutionService
from app.services.reminder_service import ReminderService
from app.services.reminder_execution_service import ReminderExecutionService

from app.agents.payment_message_agent import PaymentMessageAgent
from app.agents.confidence_checker import ConfidenceChecker

from app.agents.payment_detection_node import PaymentDetectionNode
from app.agents.confidence_checker_node import ConfidenceCheckerNode
from app.agents.approval_creation_node import ApprovalCreationNode
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
    notification_service = WhatsAppNotificationService(
        access_token=settings.WHATSAPP_ACCESS_TOKEN,
        phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        api_version=settings.WHATSAPP_API_VERSION,
    )

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
    approval_creation_node = ApprovalCreationNode(payment_service)
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
        approval_creation_node,
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


def create_payment_approval_service(
    db=None,
) -> PaymentApprovalService:
    """Compose the human-approval service used by the approval API."""

    if db is None:
        db = SessionLocal()

    payment_repository = PaymentRepository(db)

    return PaymentApprovalService(payment_repository)


def create_reminder_service(
    db=None,
) -> ReminderService:
    """Compose the service that decides which contracts are due a reminder."""

    if db is None:
        db = SessionLocal()

    contract_service = ContractService(ContractRepository(db))
    payment_service = PaymentService(PaymentRepository(db))

    return ReminderService(contract_service, payment_service)


def create_reminder_execution_service(
    db=None,
    llm=None,
) -> ReminderExecutionService:
    """Compose the service that runs the workflow for a scheduled reminder.

    Reuses the workflow + run repository from the agent execution stack so
    reminders and messages share the same wiring and session.
    """

    if db is None:
        db = SessionLocal()

    agent_execution_service = create_agent_execution_service(db=db, llm=llm)
    payment_service = PaymentService(PaymentRepository(db))

    return ReminderExecutionService(
        agent_execution_service.agent_run_repository,
        agent_execution_service.payment_workflow,
        payment_service,
    )
