"""enrich relationship tables

Revision ID: a1b2c3d4e5f6
Revises: d1d2bc0fed86
Create Date: 2026-07-13 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "d1d2bc0fed86"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add metadata_json to entry_resources
    with op.batch_alter_table("entry_resources") as batch_op:
        batch_op.add_column(sa.Column("metadata_json", sa.JSON(), nullable=True))

    # Migrate usage data into role before dropping the column
    op.execute("UPDATE entry_assets SET role = usage WHERE role IS NULL AND usage IS NOT NULL")

    with op.batch_alter_table("entry_assets") as batch_op:
        batch_op.drop_column("usage")
        batch_op.create_index("ix_entry_assets_entry_id_position", ["entry_id", "position"])


def downgrade() -> None:
    with op.batch_alter_table("entry_assets") as batch_op:
        batch_op.drop_index("ix_entry_assets_entry_id_position")
        batch_op.add_column(sa.Column("usage", sa.String(), nullable=True))

    with op.batch_alter_table("entry_resources") as batch_op:
        batch_op.drop_column("metadata_json")
