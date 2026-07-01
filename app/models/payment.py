from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Enum,
    func,
)

from sqlalchemy.orm import relationship

from app.models.base import Base
from app.enums.payment_status import PaymentStatus
from app.enums.payment_source import PaymentSource

class Payment(Base):

    __tablename__ = "payments"

    id = Column( Integer, primary_key=True )
    
    contract_id = Column( Integer, ForeignKey("contracts.id"), nullable=False )
    
    amount = Column( Numeric(10,2), nullable=False )
    
    payment_date = Column( Date, nullable=False )
    
    status = Column( Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING )
    
    source = Column( Enum(PaymentSource), nullable=False, default=PaymentSource.MANUAL )
    
    reference_message_id = Column( String(255), nullable=True )
    
    notes = Column( String(500), nullable=True )
    
    approved_at = Column( DateTime(timezone=True), nullable=True )
    
    approved_by = Column( String(100), nullable=True )
    
    contract = relationship( "Contract", back_populates="payments" )
    
    created_at = Column( DateTime(timezone=True), server_default=func.now(), nullable=False )
    
    updated_at = Column( DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False )