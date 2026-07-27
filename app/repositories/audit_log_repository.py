from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, audit_log: AuditLog) -> AuditLog:
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def get_all(self) -> list[AuditLog]:
        return self.db.query(AuditLog).all()

    def get_by_action(self, action: str) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.action == action)
            .all()
        )
