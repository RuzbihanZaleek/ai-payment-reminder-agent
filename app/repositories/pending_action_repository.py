from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.pending_action import PendingAction
from app.ai.actions.pending_action import PendingActionStatus


class PendingActionRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, pending_action: PendingAction) -> PendingAction:
        self.db.add(pending_action)
        self.db.commit()
        self.db.refresh(pending_action)

        return pending_action

    def get_by_id(self, action_id: int) -> PendingAction | None:
        return (
            self.db.query(PendingAction)
            .filter(PendingAction.id == action_id)
            .first()
        )

    def get_latest_pending_for_user(self, user_id: int) -> PendingAction | None:
        """Most recent still-confirmable action for a user (not expired)."""

        now = datetime.now(timezone.utc)

        return (
            self.db.query(PendingAction)
            .filter(PendingAction.user_id == user_id)
            .filter(PendingAction.status == PendingActionStatus.PENDING_CONFIRMATION.value)
            .filter(PendingAction.expires_at > now)
            .order_by(PendingAction.created_at.desc())
            .first()
        )

    def get_expired(self) -> list[PendingAction]:
        """PENDING actions whose confirmation window has elapsed."""

        now = datetime.now(timezone.utc)

        return (
            self.db.query(PendingAction)
            .filter(PendingAction.status == PendingActionStatus.PENDING_CONFIRMATION.value)
            .filter(PendingAction.expires_at <= now)
            .all()
        )

    def set_status(self, action_id: int, status: PendingActionStatus) -> PendingAction | None:
        action = self.get_by_id(action_id)

        if action is None:
            return None

        action.status = status.value
        self.db.commit()
        self.db.refresh(action)

        return action

    def get_by_user(self, user_id: int) -> list[PendingAction]:
        return (
            self.db.query(PendingAction)
            .filter(PendingAction.user_id == user_id)
            .order_by(PendingAction.created_at.desc())
            .all()
        )
