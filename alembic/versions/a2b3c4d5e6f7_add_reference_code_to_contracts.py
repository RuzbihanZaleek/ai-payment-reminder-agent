"""add reference_code to contracts

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add nullable first so existing rows can be backfilled before the
    # NOT NULL + UNIQUE constraints are enforced.
    op.add_column(
        'contracts',
        sa.Column('reference_code', sa.String(length=50), nullable=True),
    )
    op.execute(
        "UPDATE contracts SET reference_code = 'INV' || id "
        "WHERE reference_code IS NULL"
    )
    op.alter_column('contracts', 'reference_code', nullable=False)
    op.create_unique_constraint(
        'uq_contracts_reference_code',
        'contracts',
        ['reference_code'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'uq_contracts_reference_code',
        'contracts',
        type_='unique',
    )
    op.drop_column('contracts', 'reference_code')