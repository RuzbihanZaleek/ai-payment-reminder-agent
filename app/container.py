from app.db.session import SessionLocal

from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.agent_event_repository import AgentEventRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.contract_repository import ContractRepository
from app.repositories.reminder_log_repository import ReminderLogRepository
from app.repositories.scheduler_run_repository import SchedulerRunRepository
from app.repositories.scheduler_event_repository import SchedulerEventRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_message_repository import (
    ConversationMessageRepository,
)
from app.repositories.conversation_summary_repository import (
    ConversationSummaryRepository,
)
from app.repositories.payment_receipt_repository import PaymentReceiptRepository

from app.core.config import settings

from app.services.payment_service import PaymentService
from app.services.contract_service import ContractService
from app.services.whatsapp_notification_service import WhatsAppNotificationService
from app.services.payment_allocation_service import PaymentAllocationService
from app.services.payment_allocation_formatter import PaymentAllocationFormatter
from app.services.payment_receipt_service import PaymentReceiptService
from app.services.payment_approval_service import PaymentApprovalService
from app.services.agent_execution_service import AgentExecutionService
from app.services.reminder_service import ReminderService
from app.services.reminder_policy_service import ReminderPolicyService
from app.services.reminder_execution_service import ReminderExecutionService
from app.services.conversation_memory_service import ConversationMemoryService

from app.agents.payment_message_agent import PaymentMessageAgent
from app.agents.confidence_checker import ConfidenceChecker

from app.agents.payment_detection_node import PaymentDetectionNode
from app.agents.confidence_checker_node import ConfidenceCheckerNode
from app.agents.contract_resolver_node import ContractResolverNode
from app.agents.payment_allocation_node import PaymentAllocationNode
from app.agents.approval_creation_node import ApprovalCreationNode
from app.agents.payment_creation_node import PaymentCreationNode
from app.agents.balance_update_node import BalanceUpdateNode
from app.agents.payment_receipt_node import PaymentReceiptNode
from app.agents.reminder_decision_node import ReminderDecisionNode
from app.agents.response_generation_node import ResponseGenerationNode
from app.agents.notification_node import NotificationNode

from app.agents.workflow_executor import WorkflowExecutor
from app.agents.payment_workflow import PaymentWorkflow
from app.agents.reminder_workflow import ReminderWorkflow


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
    reminder_log_repository = ReminderLogRepository(db)
    payment_receipt_repository = PaymentReceiptRepository(db)

    # Services.
    payment_service = PaymentService(payment_repository)
    contract_service = ContractService(contract_repository)
    payment_allocation_service = PaymentAllocationService(payment_service)
    payment_receipt_service = PaymentReceiptService(
        payment_receipt_repository,
        contract_service,
        payment_service,
        PaymentAllocationFormatter(),
    )
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
    contract_resolver_node = ContractResolverNode()
    payment_allocation_node = PaymentAllocationNode(payment_allocation_service)
    approval_creation_node = ApprovalCreationNode(payment_service)
    payment_creation_node = PaymentCreationNode(payment_service)
    balance_update_node = BalanceUpdateNode(payment_service, contract_service)
    payment_receipt_node = PaymentReceiptNode(payment_receipt_service)
    reminder_decision_node = ReminderDecisionNode()
    response_generation_node = ResponseGenerationNode(
        PaymentAllocationFormatter()
    )
    notification_node = NotificationNode(
        notification_service,
        reminder_log_repository,
    )

    # Infrastructure -- receives the shared AgentRunRepository.
    workflow_executor = WorkflowExecutor(
        agent_run_repository,
        agent_event_repository,
    )

    # Workflow.
    payment_workflow = PaymentWorkflow(
        payment_detection_node,
        confidence_checker_node,
        contract_resolver_node,
        payment_allocation_node,
        approval_creation_node,
        payment_creation_node,
        balance_update_node,
        payment_receipt_node,
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


def create_reminder_policy_service(
    db=None,
) -> ReminderPolicyService:
    """Compose the policy that holds the reminder business rules."""

    if db is None:
        db = SessionLocal()

    payment_repository = PaymentRepository(db)
    payment_service = PaymentService(payment_repository)
    reminder_log_repository = ReminderLogRepository(db)

    return ReminderPolicyService(
        payment_service,
        payment_repository,
        reminder_log_repository,
    )


def create_reminder_service(
    db=None,
) -> ReminderService:
    """Compose the service that decides which contracts are due a reminder."""

    if db is None:
        db = SessionLocal()

    contract_service = ContractService(ContractRepository(db))
    reminder_policy_service = create_reminder_policy_service(db=db)

    return ReminderService(contract_service, reminder_policy_service)


def create_reminder_workflow(
    db=None,
) -> ReminderWorkflow:
    """Compose the message-free workflow used for scheduled reminders.

    Deliberately has no PaymentDetectionNode / ConfidenceChecker -- a reminder
    has no incoming message to analyse.
    """

    if db is None:
        db = SessionLocal()

    agent_run_repository = AgentRunRepository(db)
    agent_event_repository = AgentEventRepository(db)
    reminder_log_repository = ReminderLogRepository(db)

    workflow_executor = WorkflowExecutor(
        agent_run_repository,
        agent_event_repository,
    )

    notification_service = WhatsAppNotificationService(
        access_token=settings.WHATSAPP_ACCESS_TOKEN,
        phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        api_version=settings.WHATSAPP_API_VERSION,
    )

    return ReminderWorkflow(
        ReminderDecisionNode(),
        ResponseGenerationNode(PaymentAllocationFormatter()),
        NotificationNode(notification_service, reminder_log_repository),
        workflow_executor,
    )


def create_reminder_execution_service(
    db=None,
) -> ReminderExecutionService:
    """Compose the service that runs the reminder workflow for a contract."""

    if db is None:
        db = SessionLocal()

    reminder_workflow = create_reminder_workflow(db=db)

    # Share the same AgentRunRepository the workflow's executor uses, so the
    # run created here and marked completed there refer to the same row.
    agent_run_repository = reminder_workflow.workflow_executor.agent_run_repository

    payment_service = PaymentService(PaymentRepository(db))

    return ReminderExecutionService(
        agent_run_repository,
        reminder_workflow,
        payment_service,
    )


def create_scheduler_run_repository(
    db=None,
) -> SchedulerRunRepository:
    """Compose the repository that tracks scheduler runs."""

    if db is None:
        db = SessionLocal()

    return SchedulerRunRepository(db)


def create_scheduler_event_repository(
    db=None,
) -> SchedulerEventRepository:
    """Compose the repository that tracks per-contract scheduler events."""

    if db is None:
        db = SessionLocal()

    return SchedulerEventRepository(db)


def create_conversation_memory_service(
    db=None,
) -> ConversationMemoryService:
    """Compose the conversation memory service used by the WhatsApp webhook."""

    if db is None:
        db = SessionLocal()

    conversation_repository = ConversationRepository(db)
    conversation_message_repository = ConversationMessageRepository(db)
    conversation_summary_repository = ConversationSummaryRepository(db)

    return ConversationMemoryService(
        conversation_repository,
        conversation_message_repository,
        conversation_summary_repository,
    )
