"""Audit trail service.

Records security/business-relevant actions to an append-only table. Callers pass
only non-sensitive context in ``metadata`` -- never passwords, tokens or keys.
Well-known action names are exposed as constants to keep them consistent.
"""

from app.core.logger import get_logger
from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository


logger = get_logger(__name__)


class AuditService:

    # Well-known actions.
    USER_LOGIN = "USER_LOGIN"
    USER_LOGIN_FAILED = "USER_LOGIN_FAILED"
    CONTRACT_CREATED = "CONTRACT_CREATED"
    PAYMENT_APPROVED = "PAYMENT_APPROVED"
    PAYMENT_REJECTED = "PAYMENT_REJECTED"
    ASSISTANT_QUERY = "ASSISTANT_QUERY"
    ASSISTANT_RESPONSE = "ASSISTANT_RESPONSE"
    AI_MEMORY_CREATED = "AI_MEMORY_CREATED"
    AI_PROACTIVE_ANALYSIS = "AI_PROACTIVE_ANALYSIS"
    AI_RECOMMENDATION_GENERATED = "AI_RECOMMENDATION_GENERATED"
    AI_ACTION_CREATED = "AI_ACTION_CREATED"
    AI_ACTION_CONFIRMED = "AI_ACTION_CONFIRMED"
    AI_ACTION_CANCELLED = "AI_ACTION_CANCELLED"
    AI_ACTION_EXECUTED = "AI_ACTION_EXECUTED"
    AI_ACTION_EXPIRED = "AI_ACTION_EXPIRED"

    def __init__(self, repository: AuditLogRepository):
        self.repository = repository

    def record(
        self,
        action: str,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:

        audit_log = self.repository.create(
            AuditLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata_json=metadata,
            )
        )

        logger.info(
            "audit_event_recorded",
            extra={
                "audit_action": action,
                "user_id": user_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
        )

        return audit_log
