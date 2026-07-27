"""extend notification_outbox for the delivery worker

Adds worker columns to notification_outbox: attempt_count, last_error, sent_at,
available_at. Server defaults keep existing rows valid (attempt_count=0,
available_at=now).

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-07-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'notification_outbox',
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
    )
    op.add_column(
        'notification_outbox',
        sa.Column('last_error', sa.Text(), nullable=True),
    )
    op.add_column(
        'notification_outbox',
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'notification_outbox',
        sa.Column(
            'available_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_index(
        'ix_notification_outbox_available_at',
        'notification_outbox',
        ['available_at'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notification_outbox_available_at', table_name='notification_outbox')
    op.drop_column('notification_outbox', 'available_at')
    op.drop_column('notification_outbox', 'sent_at')
    op.drop_column('notification_outbox', 'last_error')
    op.drop_column('notification_outbox', 'attempt_count')
