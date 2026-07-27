"""add performance indexes

Adds indexes to the columns that existing queries filter, join or order on:
tenant scoping (contract.user_id), WhatsApp lookups, status filters, foreign
keys used by reporting joins, and the chronological columns used for
newest/oldest-first ordering and date-range filtering.

Columns that are already unique (contracts.reference_code, users.email,
processed_messages.message_id, conversation_summaries.conversation_id) are
skipped -- their unique constraint already creates a backing index.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (index_name, table, column)
_INDEXES = [
    ("ix_payments_contract_id", "payments", "contract_id"),
    ("ix_payments_status", "payments", "status"),
    ("ix_payments_approval_status", "payments", "approval_status"),
    ("ix_payments_created_at", "payments", "created_at"),
    ("ix_payments_payment_date", "payments", "payment_date"),

    ("ix_contracts_user_id", "contracts", "user_id"),
    ("ix_contracts_whatsapp_chat_id", "contracts", "whatsapp_chat_id"),
    ("ix_contracts_status", "contracts", "status"),

    ("ix_agent_runs_contract_id", "agent_runs", "contract_id"),
    ("ix_agent_runs_status", "agent_runs", "status"),
    ("ix_agent_runs_created_at", "agent_runs", "created_at"),

    ("ix_agent_events_agent_run_id", "agent_events", "agent_run_id"),
    ("ix_agent_events_created_at", "agent_events", "created_at"),

    ("ix_reminder_logs_contract_id", "reminder_logs", "contract_id"),
    ("ix_reminder_logs_sent_at", "reminder_logs", "sent_at"),

    ("ix_conversation_messages_conversation_id", "conversation_messages", "conversation_id"),
    ("ix_conversation_messages_created_at", "conversation_messages", "created_at"),

    ("ix_scheduler_events_scheduler_run_id", "scheduler_events", "scheduler_run_id"),
    ("ix_scheduler_events_contract_id", "scheduler_events", "contract_id"),

    ("ix_payment_receipts_contract_id", "payment_receipts", "contract_id"),
    ("ix_payment_receipts_payment_id", "payment_receipts", "payment_id"),
    ("ix_payment_receipts_agent_run_id", "payment_receipts", "agent_run_id"),
]


def upgrade() -> None:
    """Upgrade schema."""
    for name, table, column in _INDEXES:
        op.create_index(name, table, [column])


def downgrade() -> None:
    """Downgrade schema."""
    for name, table, _column in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
