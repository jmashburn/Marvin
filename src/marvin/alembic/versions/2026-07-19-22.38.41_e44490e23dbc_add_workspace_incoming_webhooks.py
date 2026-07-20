"""add workspace incoming webhooks

Revision ID: e44490e23dbc
Revises: b1dbbd08d7fd
Create Date: 2026-07-19 22:38:41.318375

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = 'e44490e23dbc'
down_revision: Union[str, None] = 'b1dbbd08d7fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_incoming_webhooks",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("token", sa.String(), nullable=True),
        sa.Column("received_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "slug", name="uq_incoming_webhooks_group_slug"),
    )
    op.create_index("ix_workspace_incoming_webhooks_group_id", "workspace_incoming_webhooks", ["group_id"])
    op.create_index(
        "ix_workspace_incoming_webhooks_token", "workspace_incoming_webhooks", ["token"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_incoming_webhooks_token", table_name="workspace_incoming_webhooks")
    op.drop_index("ix_workspace_incoming_webhooks_group_id", table_name="workspace_incoming_webhooks")
    op.drop_table("workspace_incoming_webhooks")
