"""ingredient normalization schema

Revision ID: 539387eab2be
Revises: f67f683f4e28
Create Date: 2026-08-06 00:00:03.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '539387eab2be'
down_revision: Union[str, Sequence[str], None] = 'f67f683f4e28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extends the existing `ingredients` table in place - it is not dropped or
    # recreated. `name` and its unique constraint (ingredients_name_key) are
    # left untouched for backward compatibility with GET /ingredients/map.
    op.add_column('ingredients', sa.Column('canonical_name_pl', sa.String(), nullable=True))
    op.add_column('ingredients', sa.Column('canonical_name_en', sa.String(), nullable=True))
    op.add_column('ingredients', sa.Column('default_store_section_id', sa.Integer(), nullable=True))
    # created_at/updated_at: add nullable, backfill, then tighten to NOT NULL.
    # SQLite's ALTER TABLE ADD COLUMN rejects non-constant defaults (e.g.
    # CURRENT_TIMESTAMP) outright, so a server_default on add_column isn't
    # portable here - this two-step form works on both SQLite and Postgres.
    # `ingredients` has 0 rows in production today, but this stays correct
    # even if a dev/RC copy already has some.
    op.add_column('ingredients', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('ingredients', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.execute("UPDATE ingredients SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    op.execute("UPDATE ingredients SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    # SQLite has no ALTER-based constraint/nullability support - batch mode
    # (copy-and-move) is required there and is a harmless wrapper on Postgres.
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.alter_column('created_at', existing_type=sa.DateTime(), nullable=False)
        batch_op.alter_column('updated_at', existing_type=sa.DateTime(), nullable=False)
        batch_op.create_foreign_key(
            'fk_ingredients_default_store_section_id',
            'store_sections',
            ['default_store_section_id'], ['id'],
        )

    op.create_table(
        'ingredient_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=False),
        sa.Column('alias_text', sa.String(), nullable=False),
        sa.Column('language', sa.String(length=2), nullable=True),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alias_text'),
    )
    op.create_index(op.f('ix_ingredient_aliases_id'), 'ingredient_aliases', ['id'], unique=False)
    op.create_index(op.f('ix_ingredient_aliases_ingredient_id'), 'ingredient_aliases', ['ingredient_id'], unique=False)

    op.create_table(
        'recipe_ingredients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.Integer(), nullable=False),
        sa.Column('ingredient_id', sa.Integer(), nullable=True),
        sa.Column('original_text', sa.String(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['ingredient_id'], ['ingredients.id']),
        sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recipe_ingredients_id'), 'recipe_ingredients', ['id'], unique=False)
    op.create_index(op.f('ix_recipe_ingredients_ingredient_id'), 'recipe_ingredients', ['ingredient_id'], unique=False)
    op.create_index(op.f('ix_recipe_ingredients_recipe_id'), 'recipe_ingredients', ['recipe_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_recipe_ingredients_recipe_id'), table_name='recipe_ingredients')
    op.drop_index(op.f('ix_recipe_ingredients_ingredient_id'), table_name='recipe_ingredients')
    op.drop_index(op.f('ix_recipe_ingredients_id'), table_name='recipe_ingredients')
    op.drop_table('recipe_ingredients')

    op.drop_index(op.f('ix_ingredient_aliases_ingredient_id'), table_name='ingredient_aliases')
    op.drop_index(op.f('ix_ingredient_aliases_id'), table_name='ingredient_aliases')
    op.drop_table('ingredient_aliases')

    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.drop_constraint('fk_ingredients_default_store_section_id', type_='foreignkey')
    op.drop_column('ingredients', 'updated_at')
    op.drop_column('ingredients', 'created_at')
    op.drop_column('ingredients', 'default_store_section_id')
    op.drop_column('ingredients', 'canonical_name_en')
    op.drop_column('ingredients', 'canonical_name_pl')
