"""add workspace_ai_settings table

Revision ID: a9b0c1d2e3f4
Revises: 278ea16934c3
Create Date: 2026-07-16 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = 'a9b0c1d2e3f4'
down_revision: Union[str, None] = 'c4e65168ca23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_ai_settings",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("credential_mode", sa.String(), nullable=False, server_default="platform"),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("secret_ref", sa.String(), nullable=True),
        sa.Column("approval_mode", sa.String(), nullable=False, server_default="suggest-only"),
        sa.Column("invocation_sources", sa.JSON(), nullable=True),
        sa.Column("operation_overrides", sa.JSON(), nullable=True),
        sa.Column("budget_config", sa.JSON(), nullable=True),
        sa.Column("logging_config", sa.JSON(), nullable=True),
        sa.Column("moderation_config", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id"),
    )
    op.create_index("ix_workspace_ai_settings_group_id", "workspace_ai_settings", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_ai_settings_group_id", table_name="workspace_ai_settings")
    op.drop_table("workspace_ai_settings")
