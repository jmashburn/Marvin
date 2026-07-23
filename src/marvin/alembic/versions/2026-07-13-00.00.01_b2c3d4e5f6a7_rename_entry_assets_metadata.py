"""rename entry_assets metadata to metadata_json

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-13 00:00:01.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("entry_assets") as batch_op:
        batch_op.alter_column("metadata", new_column_name="metadata_json")


def downgrade() -> None:
    with op.batch_alter_table("entry_assets") as batch_op:
        batch_op.alter_column("metadata_json", new_column_name="metadata")
