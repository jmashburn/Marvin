"""create workspace_variables table

Plain-text workspace-scoped key-value config referenced via {{SLUG}}.
Secrets take priority over Variables on slug collision.

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
Create Date: 2026-07-15 00:00:03.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
import marvin.db.migration_types

revision: str = "c3d4e5f6a7b9"
down_revision: str | None = "b2c3d4e5f6a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_variables",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "slug", name="uq_workspace_variables_group_slug"),
    )
    op.create_index("ix_workspace_variables_group_id", "workspace_variables", ["group_id"])
    op.create_index("ix_workspace_variables_slug", "workspace_variables", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_workspace_variables_slug", table_name="workspace_variables")
    op.drop_index("ix_workspace_variables_group_id", table_name="workspace_variables")
    op.drop_table("workspace_variables")
