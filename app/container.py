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
from app.repositories.user_repository import UserRepository
from app.repositories.notification_outbox_repository import (
    NotificationOutboxRepository,
)
from app.repositories.audit_log_repository import AuditLogRepository

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
from app.services.contract_reporting_service import ContractReportingService
from app.services.payment_reporting_service import PaymentReportingService
from app.services.receipt_reporting_service import ReceiptReportingService
from app.services.agent_reporting_service import AgentReportingService
from app.services.scheduler_reporting_service import SchedulerReportingService
from app.services.reminder_reporting_service import ReminderReportingService
from app.services.dashboard_service import DashboardService
from app.services.contract_analytics_service import ContractAnalyticsService
from app.services.payment_analytics_service import PaymentAnalyticsService
from app.services.reminder_analytics_service import ReminderAnalyticsService
from app.services.agent_analytics_service import AgentAnalyticsService
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.notification_outbox_service import NotificationOutboxService
from app.services.notification_recovery_service import NotificationRecoveryService
from app.services.system_reporting_service import SystemReportingService
from app.services.audit_service import AuditService
from app.services.alert_service import AlertService, LoggingAlertService

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
        max_retries=settings.WHATSAPP_MAX_RETRIES,
        retry_delay_seconds=settings.WHATSAPP_RETRY_DELAY_SECONDS,
        timeout_seconds=settings.WHATSAPP_TIMEOUT_SECONDS,
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
        notification_outbox_service=NotificationOutboxService(
            NotificationOutboxRepository(db)
        ),
        notification_mode=settings.NOTIFICATION_MODE,
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
    contract_repository = ContractRepository(db)

    return PaymentApprovalService(
        payment_repository,
        contract_repository,
        audit_service=create_audit_service(db=db),
    )


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
        max_retries=settings.WHATSAPP_MAX_RETRIES,
        retry_delay_seconds=settings.WHATSAPP_RETRY_DELAY_SECONDS,
        timeout_seconds=settings.WHATSAPP_TIMEOUT_SECONDS,
    )

    return ReminderWorkflow(
        ReminderDecisionNode(),
        ResponseGenerationNode(PaymentAllocationFormatter()),
        NotificationNode(
            notification_service,
            reminder_log_repository,
            notification_outbox_service=NotificationOutboxService(
                NotificationOutboxRepository(db)
            ),
            notification_mode=settings.NOTIFICATION_MODE,
        ),
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


def create_contract_reporting_service(
    db=None,
) -> ContractReportingService:
    """Compose the read-only contract summary reporting service."""

    if db is None:
        db = SessionLocal()

    contract_service = ContractService(ContractRepository(db))
    payment_service = PaymentService(PaymentRepository(db))

    return ContractReportingService(contract_service, payment_service)


def create_payment_reporting_service(
    db=None,
) -> PaymentReportingService:
    """Compose the read-only payment history reporting service."""

    if db is None:
        db = SessionLocal()

    payment_service = PaymentService(PaymentRepository(db))

    return PaymentReportingService(payment_service)


def create_receipt_reporting_service(
    db=None,
) -> ReceiptReportingService:
    """Compose the read-only receipt history reporting service."""

    if db is None:
        db = SessionLocal()

    return ReceiptReportingService(PaymentReceiptRepository(db))


def create_agent_reporting_service(
    db=None,
) -> AgentReportingService:
    """Compose the read-only agent run reporting service."""

    if db is None:
        db = SessionLocal()

    return AgentReportingService(
        AgentRunRepository(db),
        AgentEventRepository(db),
    )


def create_scheduler_reporting_service(
    db=None,
) -> SchedulerReportingService:
    """Compose the read-only scheduler run reporting service."""

    if db is None:
        db = SessionLocal()

    return SchedulerReportingService(
        SchedulerRunRepository(db),
        SchedulerEventRepository(db),
    )


def create_dashboard_service(
    db=None,
) -> DashboardService:
    """Compose the dashboard service from the existing reporting services."""

    if db is None:
        db = SessionLocal()

    return DashboardService(
        create_contract_reporting_service(db=db),
        create_payment_reporting_service(db=db),
        create_agent_reporting_service(db=db),
        create_scheduler_reporting_service(db=db),
    )


def create_reminder_reporting_service(
    db=None,
) -> ReminderReportingService:
    """Compose the read-only reminder log reporting service."""

    if db is None:
        db = SessionLocal()

    return ReminderReportingService(ReminderLogRepository(db))


def create_analytics_service(
    db=None,
) -> AnalyticsService:
    """Compose the analytics service from the existing reporting services."""

    if db is None:
        db = SessionLocal()

    return AnalyticsService(
        ContractAnalyticsService(create_contract_reporting_service(db=db)),
        PaymentAnalyticsService(create_payment_reporting_service(db=db)),
        ReminderAnalyticsService(
            create_reminder_reporting_service(db=db),
            create_scheduler_reporting_service(db=db),
        ),
        AgentAnalyticsService(create_agent_reporting_service(db=db)),
    )


def create_notification_outbox_service(
    db=None,
) -> NotificationOutboxService:
    """Compose the notification outbox service (records pending notifications)."""

    if db is None:
        db = SessionLocal()

    return NotificationOutboxService(NotificationOutboxRepository(db))


def create_alert_service() -> AlertService:
    """Compose the operational alert service (log-based by default)."""

    return LoggingAlertService()


def create_notification_recovery_service(
    db=None,
) -> NotificationRecoveryService:
    """Compose the dead-letter recovery service used by the admin API."""

    if db is None:
        db = SessionLocal()

    return NotificationRecoveryService(NotificationOutboxRepository(db))


def create_system_reporting_service(
    db=None,
) -> SystemReportingService:
    """Compose the operational system-health reporting service."""

    if db is None:
        db = SessionLocal()

    return SystemReportingService(
        NotificationOutboxRepository(db),
        SchedulerRunRepository(db),
    )


def create_notification_worker(
    db=None,
):
    """Compose the notification outbox worker (drains PENDING notifications)."""

    from app.workers.notification_worker import NotificationWorker

    if db is None:
        db = SessionLocal()

    notification_service = WhatsAppNotificationService(
        access_token=settings.WHATSAPP_ACCESS_TOKEN,
        phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        api_version=settings.WHATSAPP_API_VERSION,
        max_retries=settings.WHATSAPP_MAX_RETRIES,
        retry_delay_seconds=settings.WHATSAPP_RETRY_DELAY_SECONDS,
        timeout_seconds=settings.WHATSAPP_TIMEOUT_SECONDS,
    )

    return NotificationWorker(
        NotificationOutboxRepository(db),
        notification_service,
        max_retries=settings.NOTIFICATION_MAX_RETRIES,
        retry_base_delay_seconds=settings.WHATSAPP_RETRY_DELAY_SECONDS,
        batch_size=settings.NOTIFICATION_WORKER_BATCH_SIZE,
        processing_timeout_minutes=settings.NOTIFICATION_PROCESSING_TIMEOUT_MINUTES,
        failure_alert_threshold=settings.NOTIFICATION_FAILURE_ALERT_THRESHOLD,
        alert_service=create_alert_service(),
    )


def create_audit_service(
    db=None,
) -> AuditService:
    """Compose the audit-trail service."""

    if db is None:
        db = SessionLocal()

    return AuditService(AuditLogRepository(db))


def create_contract_service(
    db=None,
) -> ContractService:
    """Compose the write-path ContractService (with audit) for contract creation."""

    if db is None:
        db = SessionLocal()

    return ContractService(
        ContractRepository(db),
        audit_service=create_audit_service(db=db),
    )


def create_auth_service(
    db=None,
) -> AuthService:
    """Compose the authentication service."""

    if db is None:
        db = SessionLocal()

    return AuthService(
        UserRepository(db),
        audit_service=create_audit_service(db=db),
    )
