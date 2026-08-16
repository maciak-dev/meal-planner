"""add stores and ingredient preferred store

Revision ID: 7a1c2d4e5f60
Revises: 69eea78ac02c
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a1c2d4e5f60"
down_revision: Union[str, Sequence[str], None] = "69eea78ac02c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_stores_id"), "stores", ["id"], unique=False)
    op.add_column("ingredients", sa.Column("preferred_store_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.create_foreign_key(
            "fk_ingredients_preferred_store_id", "stores", ["preferred_store_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.drop_constraint("fk_ingredients_preferred_store_id", type_="foreignkey")
    op.drop_column("ingredients", "preferred_store_id")
    op.drop_index(op.f("ix_stores_id"), table_name="stores")
    op.drop_table("stores")
