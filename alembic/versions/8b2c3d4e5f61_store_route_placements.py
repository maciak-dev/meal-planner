"""add per-store sections and ingredient route placements

Revision ID: 8b2c3d4e5f61
Revises: 7a1c2d4e5f60
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8b2c3d4e5f61"
down_revision: Union[str, Sequence[str], None] = "7a1c2d4e5f60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("store_sections", sa.Column("store_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("store_sections") as batch_op:
        batch_op.create_foreign_key("fk_store_sections_store_id", "stores", ["store_id"], ["id"])
        batch_op.create_index("ix_store_sections_store_id", ["store_id"], unique=False)

    op.create_table(
        "ingredient_store_placements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("store_section_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["ingredient_id"], ["ingredients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_section_id"], ["store_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "ingredient_id", name="uq_store_ingredient"),
    )
    for column in ("id", "store_id", "ingredient_id", "store_section_id"):
        op.create_index(f"ix_ingredient_store_placements_{column}", "ingredient_store_placements", [column], unique=False)


def downgrade() -> None:
    for column in ("store_section_id", "ingredient_id", "store_id", "id"):
        op.drop_index(f"ix_ingredient_store_placements_{column}", table_name="ingredient_store_placements")
    op.drop_table("ingredient_store_placements")
    with op.batch_alter_table("store_sections") as batch_op:
        batch_op.drop_index("ix_store_sections_store_id")
        batch_op.drop_constraint("fk_store_sections_store_id", type_="foreignkey")
    op.drop_column("store_sections", "store_id")
