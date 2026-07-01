from decimal import Decimal
from app.agents.state import AgentState


def test_agent_state_structure():

    state: AgentState = {
        "contract_id": 1,
        "whatsapp_chat_id": "friend_chat_123",

        "total_amount": Decimal("2200"),
        "daily_amount": Decimal("20"),
        "total_paid": Decimal("920"),
        "remaining_amount": Decimal("1280"),

        "pending_dates": [],
        "pending_amount": Decimal("0"),

        "message_id": None,
        "incoming_message": None,
        "detected_payment_amount": None,

        "requires_approval": True,
        "approval_status": "PENDING",

        "generated_message": None,
    }

    assert state["contract_id"] == 1
    assert state["remaining_amount"] == Decimal("1280")