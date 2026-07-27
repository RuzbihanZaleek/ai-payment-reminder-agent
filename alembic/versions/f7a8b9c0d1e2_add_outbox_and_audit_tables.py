"""add notification_outbox and audit_logs tables

Phase 10.5: durable notification outbox (recoverable delivery) and an
append-only audit trail.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'notification_outbox',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.Integer(), nullable=True),
        sa.Column('agent_run_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=50), server_default='whatsapp', nullable=False),
        sa.Column('recipient', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id']),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_outbox_contract_id', 'notification_outbox', ['contract_id'])
    op.create_index('ix_notification_outbox_agent_run_id', 'notification_outbox', ['agent_run_id'])
    op.create_index('ix_notification_outbox_status', 'notification_outbox', ['status'])

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index('ix_notification_outbox_status', table_name='notification_outbox')
    op.drop_index('ix_notification_outbox_agent_run_id', table_name='notification_outbox')
    op.drop_index('ix_notification_outbox_contract_id', table_name='notification_outbox')
    op.drop_table('notification_outbox')
