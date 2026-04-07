"""add_scan_credits

Revision ID: 3f8c1a92e4b7
Revises: d99ddb235da3
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3f8c1a92e4b7'
down_revision: Union[str, Sequence[str], None] = 'd99ddb235da3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('scan_credits', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'scan_credits')
