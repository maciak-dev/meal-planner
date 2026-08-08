"""recipe import source fields

Revision ID: 8f9e43e7e225
Revises: 539387eab2be
Create Date: 2026-08-06 00:00:04.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8f9e43e7e225'
down_revision: Union[str, Sequence[str], None] = '539387eab2be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All nullable: only recipes actually imported from a URL get these set.
    op.add_column('recipes', sa.Column('source_url', sa.String(), nullable=True))
    op.add_column('recipes', sa.Column('source_name', sa.String(), nullable=True))
    op.add_column('recipes', sa.Column('source_author', sa.String(), nullable=True))
    op.add_column('recipes', sa.Column('imported_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('recipes', 'imported_at')
    op.drop_column('recipes', 'source_author')
    op.drop_column('recipes', 'source_name')
    op.drop_column('recipes', 'source_url')
