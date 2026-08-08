"""recipe translations table

Revision ID: 5a84c10939a0
Revises: d17abcef39ac
Create Date: 2026-08-06 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5a84c10939a0'
down_revision: Union[str, Sequence[str], None] = 'd17abcef39ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema only - no automatic backfill here. Existing 64 recipes get their
    # 'pl' translation row via scripts/backfill_recipe_translations.py, run
    # manually and reviewed, not as part of this migration.
    op.create_table(
        'recipe_translations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=2), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('instructions', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_id', 'language', name='uq_recipe_translations_recipe_language'),
    )
    op.create_index(op.f('ix_recipe_translations_id'), 'recipe_translations', ['id'], unique=False)
    op.create_index(op.f('ix_recipe_translations_recipe_id'), 'recipe_translations', ['recipe_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_recipe_translations_recipe_id'), table_name='recipe_translations')
    op.drop_index(op.f('ix_recipe_translations_id'), table_name='recipe_translations')
    op.drop_table('recipe_translations')
