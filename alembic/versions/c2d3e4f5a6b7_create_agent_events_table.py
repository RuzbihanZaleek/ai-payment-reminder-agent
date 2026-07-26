"""create agent_events table

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('agent_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agent_run_id', sa.Integer(), nullable=False),
    sa.Column('node_name', sa.String(length=100), nullable=False),
    sa.Column('status', sa.Enum('STARTED', 'COMPLETED', 'FAILED', name='agenteventstatus'), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('agent_events')
