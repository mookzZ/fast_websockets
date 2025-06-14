"""Adjust SQLAlchemy relationships

Revision ID: 35929343648d
Revises: cd8ba36e35f4
Create Date: 2025-06-09 21:53:20.499067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '35929343648d'
down_revision: Union[str, None] = 'cd8ba36e35f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('chat_members', 'joined_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('chats', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('chats', 'creator_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('chats', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    op.alter_column('messages', 'timestamp',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=True,
               existing_server_default=sa.text('now()'))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('messages', 'timestamp',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('chats', 'created_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('chats', 'creator_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('chats', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('chat_members', 'joined_at',
               existing_type=postgresql.TIMESTAMP(timezone=True),
               nullable=False,
               existing_server_default=sa.text('now()'))
    # ### end Alembic commands ###
