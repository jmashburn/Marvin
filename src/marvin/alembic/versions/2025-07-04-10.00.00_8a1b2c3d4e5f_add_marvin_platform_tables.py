"""Add entry types and entries

Revision ID: 8a1b2c3d4e5f
Revises: 096bd305c0d2
Create Date: 2025-07-04 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = "8a1b2c3d4e5f"
down_revision: Union[str, None] = "096bd305c0d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entry_types",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "slug"),
    )
    op.create_index(op.f("ix_entry_types_group_id"), "entry_types", ["group_id"], unique=False)

    op.create_table(
        "entries",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("entry_type_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="inbox", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["entry_type_id"], ["entry_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "slug"),
    )
    op.create_index(op.f("ix_entries_entry_type_id"), "entries", ["entry_type_id"], unique=False)
    op.create_index(op.f("ix_entries_group_id"), "entries", ["group_id"], unique=False)
    op.create_index("ix_entries_group_status", "entries", ["group_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_entries_group_status", table_name="entries")
    op.drop_index(op.f("ix_entries_group_id"), table_name="entries")
    op.drop_index(op.f("ix_entries_entry_type_id"), table_name="entries")
    op.drop_table("entries")

    op.drop_index(op.f("ix_entry_types_group_id"), table_name="entry_types")
    op.drop_table("entry_types")
