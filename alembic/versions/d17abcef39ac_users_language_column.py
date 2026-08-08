"""users language column

Revision ID: d17abcef39ac
Revises: 41e1afa8db94
Create Date: 2026-08-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd17abcef39ac'
down_revision: Union[str, Sequence[str], None] = '41e1afa8db94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default is required: users already has rows in prod (5 as of the
    # last audit), and a NOT NULL column without a default fails on ALTER TABLE.
    op.add_column(
        'users',
        sa.Column('language', sa.String(length=2), nullable=False, server_default='pl'),
    )


def downgrade() -> None:
    op.drop_column('users', 'language')
