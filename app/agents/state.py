from typing import TypedDict, Optional
from datetime import date
from decimal import Decimal


class AgentState(TypedDict):

    # Contract information
    contract_id: int
    whatsapp_chat_id: str

    # Financial information
    total_amount: Decimal
    daily_amount: Decimal
    total_paid: Decimal
    remaining_amount: Decimal

    # Pending payment information
    pending_dates: list[date]
    pending_amount: Decimal

    # Incoming WhatsApp message
    message_id: Optional[str]
    incoming_message: Optional[str]
    detected_payment_amount: Optional[Decimal]

    # Approval workflow
    requires_approval: bool
    approval_status: Optional[str]

    # Generated response
    generated_message: Optional[str]