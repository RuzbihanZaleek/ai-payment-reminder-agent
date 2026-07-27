from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.core.errors import NotFoundError, ErrorCode
from app.container import create_notification_recovery_service
from app.services.notification_recovery_service import NotificationRecoveryService
from app.api.deps import require_admin


# Every endpoint requires an admin (enforced at the router level).
router = APIRouter(
    prefix="/admin/notifications",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


class NotificationResponse(BaseModel):

    id: int
    contract_id: int | None
    agent_run_id: int | None
    channel: str
    recipient: str
    status: str
    attempt_count: int
    last_error: str | None
    available_at: datetime | None
    sent_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


def get_notification_recovery_service():

    db = SessionLocal()

    try:
        yield create_notification_recovery_service(db=db)
    finally:
        db.close()


@router.get("/failed", response_model=list[NotificationResponse])
def list_failed(
    service: NotificationRecoveryService = Depends(get_notification_recovery_service),
):

    return service.list_failed()


@router.get("/pending", response_model=list[NotificationResponse])
def list_pending(
    service: NotificationRecoveryService = Depends(get_notification_recovery_service),
):

    return service.list_pending()


@router.post("/{notification_id}/retry", response_model=NotificationResponse)
def retry_notification(
    notification_id: int,
    service: NotificationRecoveryService = Depends(get_notification_recovery_service),
):

    outbox = service.retry(notification_id)

    if outbox is None:
        raise NotFoundError(
            "Notification not found or not in a FAILED state.",
            code=ErrorCode.NOTIFICATION_NOT_FOUND,
        )

    return outbox


@router.post("/{notification_id}/discard", response_model=NotificationResponse)
def discard_notification(
    notification_id: int,
    service: NotificationRecoveryService = Depends(get_notification_recovery_service),
):

    outbox = service.discard(notification_id)

    if outbox is None:
        raise NotFoundError(
            "Notification not found or not in a FAILED state.",
            code=ErrorCode.NOTIFICATION_NOT_FOUND,
        )

    return outbox
