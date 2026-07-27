"""create scheduler_runs table

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'a6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('scheduler_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.Enum('RUNNING', 'COMPLETED', 'FAILED', name='schedulerrunstatus'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('total_contracts', sa.Integer(), server_default='0', nullable=False),
    sa.Column('successful_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('failed_count', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('scheduler_runs')