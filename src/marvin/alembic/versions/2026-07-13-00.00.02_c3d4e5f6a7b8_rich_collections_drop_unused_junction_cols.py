"""rich collections + drop unused junction columns

Add role and metadata_json to entry_collections.
Drop caption, focal_point from entry_assets.
Drop quantity, unit from entry_resources.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-13 00:00:02.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("entry_collections") as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))

    with op.batch_alter_table("entry_assets") as batch_op:
        batch_op.drop_column("caption")
        batch_op.drop_column("focal_point")

    with op.batch_alter_table("entry_resources") as batch_op:
        batch_op.drop_column("quantity")
        batch_op.drop_column("unit")


def downgrade() -> None:
    with op.batch_alter_table("entry_resources") as batch_op:
        batch_op.add_column(sa.Column("unit", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("quantity", sa.String(), nullable=True))

    with op.batch_alter_table("entry_assets") as batch_op:
        batch_op.add_column(sa.Column("focal_point", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("caption", sa.String(), nullable=True))

    with op.batch_alter_table("entry_collections") as batch_op:
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("role")
