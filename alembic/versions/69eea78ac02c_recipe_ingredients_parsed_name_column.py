"""recipe ingredients parsed name column

Revision ID: 69eea78ac02c
Revises: 8f9e43e7e225
Create Date: 2026-08-06 15:44:50.244869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '69eea78ac02c'
down_revision: Union[str, Sequence[str], None] = '8f9e43e7e225'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable free-text column - stores the ingredient name as the user
    # confirmed/edited it in the import draft. NOT a mapping to Ingredient
    # (that stays ingredient_id, untouched here) - just preserves the user's
    # correction instead of silently discarding it at save time.
    op.add_column('recipe_ingredients', sa.Column('parsed_name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('recipe_ingredients', 'parsed_name')
