"""add workspace_mcp_servers table + external_mcp_enabled switch

Revision ID: f7a8b9c0d1e2
Revises: a112d0c60cb7
Create Date: 2026-07-19 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "a112d0c60cb7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_mcp_servers",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("transport", sa.String(), nullable=False, server_default="http"),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("secret_ref", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allowed_tools", sa.JSON(), nullable=True),
        sa.Column("created_by", marvin.db.migration_types.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "slug", name="uq_mcp_servers_group_slug"),
    )
    op.create_index("ix_workspace_mcp_servers_group_id", "workspace_mcp_servers", ["group_id"])

    op.add_column(
        "workspace_ai_settings",
        sa.Column("external_mcp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("workspace_ai_settings", "external_mcp_enabled")
    op.drop_index("ix_workspace_mcp_servers_group_id", table_name="workspace_mcp_servers")
    op.drop_table("workspace_mcp_servers")
