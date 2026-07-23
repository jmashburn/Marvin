"""add integration_event_subscriptions

Revision ID: 058ffb19e2bb
Revises: 024ede5589c6
Create Date: 2026-07-21 21:41:48.636400

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = "058ffb19e2bb"
down_revision: str | None = "024ede5589c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Only the integration_event_subscriptions table — unrelated autogenerate drift stripped.
    op.create_table(
        "integration_event_subscriptions",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("integration_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("args", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", marvin.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column("update_at", marvin.db.migration_types.NaiveDateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_integration_event_subscriptions_group_id"), "integration_event_subscriptions", ["group_id"], unique=False)
    op.create_index(op.f("ix_integration_event_subscriptions_integration_id"), "integration_event_subscriptions", ["integration_id"], unique=False)
    op.create_index(op.f("ix_integration_event_subscriptions_event_type"), "integration_event_subscriptions", ["event_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_integration_event_subscriptions_event_type"), table_name="integration_event_subscriptions")
    op.drop_index(op.f("ix_integration_event_subscriptions_integration_id"), table_name="integration_event_subscriptions")
    op.drop_index(op.f("ix_integration_event_subscriptions_group_id"), table_name="integration_event_subscriptions")
    op.drop_table("integration_event_subscriptions")
