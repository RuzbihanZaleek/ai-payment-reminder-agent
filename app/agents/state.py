from typing import Optional
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.payment_detection import PaymentDetectionResult


class AgentState(BaseModel):

    # Incoming message
    message: str
    message_id: Optional[str] = None

    # AI detection result
    payment_detection: Optional[PaymentDetectionResult] = None

    detected_payment_amount: Optional[Decimal] = None


    # Contract information
    contract_id: Optional[int] = None
    whatsapp_chat_id: Optional[str] = None


    # Financial information
    total_amount: Optional[Decimal] = None
    daily_amount: Optional[Decimal] = None
    total_paid: Optional[Decimal] = None
    remaining_amount: Optional[Decimal] = None


    # Pending payments
    pending_dates: list[date] = []
    pending_amount: Optional[Decimal] = None


    # Approval workflow
    requires_approval: bool = False
    approval_status: Optional[str] = None


    # Generated response
    generated_message: Optional[str] = None