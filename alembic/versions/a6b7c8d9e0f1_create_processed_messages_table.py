"""create processed_messages table

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, Sequence[str], None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('processed_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.String(length=255), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('message_id', name='uq_processed_messages_message_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('processed_messages')