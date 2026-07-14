"""rename assets & resources metadata → metadata_json

Align with the metadata_json naming convention used by all other tables.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-13 00:00:03.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("assets") as batch_op:
        batch_op.alter_column("metadata", new_column_name="metadata_json")

    with op.batch_alter_table("resources") as batch_op:
        batch_op.alter_column("metadata", new_column_name="metadata_json")


def downgrade() -> None:
    with op.batch_alter_table("resources") as batch_op:
        batch_op.alter_column("metadata_json", new_column_name="metadata")

    with op.batch_alter_table("assets") as batch_op:
        batch_op.alter_column("metadata_json", new_column_name="metadata")
