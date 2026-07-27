from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.reminder_log import ReminderLog


class ReminderLogRepository:

    def __init__( self, db: Session):
        self.db = db

    def create( self, reminder_log: ReminderLog ) -> ReminderLog:
        self.db.add(reminder_log)
        self.db.commit()
        self.db.refresh(reminder_log)

        return reminder_log

    def get_all( self ) -> list[ReminderLog]:
        return (
            self.db.query(ReminderLog)
            .all()
        )

    def has_sent_today( self, contract_id: int ) -> bool:
        return (
            self.db.query(ReminderLog)
            .filter(ReminderLog.contract_id == contract_id)
            .filter(func.date(ReminderLog.sent_at) == date.today())
            .first()
            is not None
        )
