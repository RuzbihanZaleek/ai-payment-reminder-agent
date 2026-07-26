"""add approval_status to payments

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


approval_status_enum = sa.Enum(
    'PENDING', 'APPROVED', 'REJECTED', name='approvalstatus'
)


def upgrade() -> None:
    """Upgrade schema."""
    approval_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'payments',
        sa.Column(
            'approval_status',
            approval_status_enum,
            nullable=False,
            server_default='PENDING',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('payments', 'approval_status')
    approval_status_enum.drop(op.get_bind(), checkfirst=True)
