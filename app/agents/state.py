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

    # Conversation memory
    conversation_id: Optional[int] = None
    conversation_history: list = []

    # AI detection result
    # The detected amount lives on payment_detection.amount — read it there
    # rather than duplicating it onto the state.
    payment_detection: Optional[PaymentDetectionResult] = None


    # Contract information
    contract_id: Optional[int] = None
    whatsapp_chat_id: Optional[str] = None

    # Scheduled-reminder template context (populated only for reminders, used to
    # fill the WhatsApp reminder template's placeholders).
    contract_name: Optional[str] = None
    due_date: Optional[date] = None

    # Multi-contract support
    # resolved_contracts: the sender's active contracts (candidate pool,
    # lightweight dicts) resolved from the phone number.
    # contract_ids: the specific contract(s) referenced in the message.
    resolved_contracts: list = []
    contract_ids: list[int] = []

    # Automatic payment allocation: [{contract_id, amount, reference_code}]
    # produced by PaymentAllocationNode and consumed by PaymentCreationNode.
    payment_allocations: list = []

    # Human-readable allocation breakdown for the generated response.
    allocation_summary: Optional[str] = None

    # Audit: the workflow's run id, and receipt snapshots per created payment.
    agent_run_id: Optional[int] = None
    payment_receipts: list = []


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