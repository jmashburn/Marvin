"""create workspace_secrets table

Stores encrypted workspace-level secrets referenced by slug in webhooks
and other integration configs (e.g. {{CLOUDFLARE_TOKEN}}).

Revision ID: a1b2c3d4e5f7
Revises: f6a7b8c9d0e1
Create Date: 2026-07-15 00:00:01.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
import marvin.db.migration_types

revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_secrets",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "slug", name="uq_workspace_secrets_group_slug"),
    )
    op.create_index("ix_workspace_secrets_group_id", "workspace_secrets", ["group_id"])
    op.create_index("ix_workspace_secrets_slug", "workspace_secrets", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_workspace_secrets_slug", table_name="workspace_secrets")
    op.drop_index("ix_workspace_secrets_group_id", table_name="workspace_secrets")
    op.drop_table("workspace_secrets")
