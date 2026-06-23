"""add last_reminder_date to sobriety_users (dedupe daily reminders)

Revision ID: d4f7c1a92e3b
Revises: c2e6a83f51b9
Create Date: 2026-06-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4f7c1a92e3b'
down_revision: Union[str, Sequence[str], None] = 'c2e6a83f51b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sobriety_users', sa.Column('last_reminder_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('sobriety_users', 'last_reminder_date')
