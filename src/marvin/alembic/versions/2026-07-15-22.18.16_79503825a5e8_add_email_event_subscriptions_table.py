"""add email_event_subscriptions table

Revision ID: 79503825a5e8
Revises: d4e5f6a7b8ca
Create Date: 2026-07-15 22:18:16.163744

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = "79503825a5e8"
down_revision: str | None = "d4e5f6a7b8ca"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "email_event_subscriptions",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("template_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("recipient_type", sa.String(), nullable=False),
        sa.Column("recipient_field", sa.String(), nullable=True),
        sa.Column("recipient_email", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["email_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_event_subscriptions_group_id", "email_event_subscriptions", ["group_id"])
    op.create_index("ix_email_event_subscriptions_event_type", "email_event_subscriptions", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_email_event_subscriptions_event_type", table_name="email_event_subscriptions")
    op.drop_index("ix_email_event_subscriptions_group_id", table_name="email_event_subscriptions")
    op.drop_table("email_event_subscriptions")
