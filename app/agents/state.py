from typing import Optional
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.payment_detection import PaymentDetectionResult
from app.enums.reminder_decision import ReminderDecision
from app.enums.trigger_type import TriggerType


class AgentState(BaseModel):

    # What triggered this run
    trigger_type: TriggerType = TriggerType.MESSAGE

    # Incoming message
    message: str
    message_id: Optional[str] = None

    # AI detection result
    # The detected amount lives on payment_detection.amount — read it there
    # rather than duplicating it onto the state.
    payment_detection: Optional[PaymentDetectionResult] = None


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

    # Payment creation result
    payment_id: Optional[int] = None

    # Reminder decision
    decision: ReminderDecision = ReminderDecision.NONE

    # Notification result
    notification_sent: bool = False
    notification_status: Optional[str] = None