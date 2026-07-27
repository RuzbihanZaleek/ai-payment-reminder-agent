from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    func,
)

from app.models.base import Base


class User(Base):

    __tablename__ = "users"

    id = Column( Integer, primary_key=True )

    email = Column( String(255), unique=True, nullable=False )

    hashed_password = Column( String(255), nullable=False )

    is_active = Column( Boolean, nullable=False, default=True )

    # Grants access to the /admin operational endpoints.
    is_admin = Column( Boolean, nullable=False, default=False, server_default=func.false() )

    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )