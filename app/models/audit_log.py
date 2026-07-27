from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    ForeignKey,
    func,
)

from app.models.base import Base


class AuditLog(Base):
    """An append-only record of a security/business-relevant action.

    Used for the production audit trail (logins, approvals, contract creation).
    ``metadata_json`` holds non-sensitive context only -- never secrets.
    """

    __tablename__ = "audit_logs"

    id = Column( Integer, primary_key=True )

    user_id = Column( Integer, ForeignKey("users.id"), nullable=True, index=True )

    action = Column( String(100), nullable=False, index=True )

    entity_type = Column( String(100), nullable=True )

    entity_id = Column( Integer, nullable=True )

    # Column attribute is ``metadata_json`` because ``metadata`` is reserved by
    # SQLAlchemy's Declarative API; the DB column is still named "metadata".
    metadata_json = Column( "metadata", JSON, nullable=True )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False, index=True )
