"""store sections table

Revision ID: f67f683f4e28
Revises: 5a84c10939a0
Create Date: 2026-08-06 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f67f683f4e28'
down_revision: Union[str, Sequence[str], None] = '5a84c10939a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # V1: one global, flat list of sections with a single sort_order (no
    # per-store variants yet) - kept deliberately simple, see
    # docs/decisions/ingredient-normalization.md.
    op.create_table(
        'store_sections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name_pl', sa.String(), nullable=False),
        sa.Column('name_en', sa.String(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_store_sections_id'), 'store_sections', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_store_sections_id'), table_name='store_sections')
    op.drop_table('store_sections')
