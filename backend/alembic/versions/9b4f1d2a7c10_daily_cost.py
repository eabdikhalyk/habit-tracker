"""add daily_cost to sobriety_users

Revision ID: 9b4f1d2a7c10
Revises: 7a1c2e9b3d44
Create Date: 2026-06-19 00:00:00.000001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9b4f1d2a7c10'
down_revision: Union[str, Sequence[str], None] = '7a1c2e9b3d44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sobriety_users', sa.Column('daily_cost', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    op.drop_column('sobriety_users', 'daily_cost')
