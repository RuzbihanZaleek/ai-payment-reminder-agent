"""create payment_receipts table

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('payment_receipts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agent_run_id', sa.Integer(), nullable=False),
    sa.Column('contract_id', sa.Integer(), nullable=False),
    sa.Column('payment_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('previous_balance', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('new_balance', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('allocation_summary', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ),
    sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ),
    sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('payment_receipts')