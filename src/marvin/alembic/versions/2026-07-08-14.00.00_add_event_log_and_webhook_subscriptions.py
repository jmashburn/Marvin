"""Add event_log table and webhook event subscriptions

Revision ID: b5c9d3f2e4a7
Revises: a3f8e9c4d2b1
Create Date: 2026-07-08 14:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID


# Determine if we're using PostgreSQL
def is_postgresql():
    """Check if the database is PostgreSQL."""
    return op.get_bind().dialect.name == "postgresql"


# revision identifiers, used by Alembic.
revision = "b5c9d3f2e4a7"
down_revision = "a3f8e9c4d2b1"
branch_labels = None
depends_on = None


def upgrade():
    # Determine column types based on database
    use_pg = is_postgresql()
    uuid_type = UUID() if use_pg else sa.String(36)
    json_type = JSONB() if use_pg else sa.JSON()
    array_type = ARRAY(sa.String()) if use_pg else sa.Text()  # Store as JSON text in SQLite

    # Create event_log table
    op.create_table(
        "event_log",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("event_id", uuid_type, nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workspace_id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=True),
        sa.Column("entity_id", uuid_type, nullable=True),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("integration_id", sa.String(), nullable=False),
        sa.Column("operation", sa.String(), nullable=True),
        sa.Column("event_data", json_type, nullable=False),
        sa.Column("message_title", sa.String(), nullable=False),
        sa.Column("message_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    # Create indexes for event_log
    op.create_index("ix_event_log_event_id", "event_log", ["event_id"], unique=True)
    op.create_index("ix_event_log_event_type", "event_log", ["event_type"])
    op.create_index("ix_event_log_occurred_at", "event_log", ["occurred_at"])
    op.create_index("ix_event_log_workspace_id", "event_log", ["workspace_id"])
    op.create_index("ix_event_log_user_id", "event_log", ["user_id"])
    op.create_index("ix_event_log_entity_id", "event_log", ["entity_id"])
    op.create_index("ix_event_log_entity_type", "event_log", ["entity_type"])

    # Composite indexes for common query patterns
    op.create_index(
        "ix_event_log_workspace_type_time",
        "event_log",
        ["workspace_id", "event_type", "occurred_at"],
    )
    op.create_index("ix_event_log_user_time", "event_log", ["user_id", "occurred_at"])
    op.create_index(
        "ix_event_log_entity",
        "event_log",
        ["entity_id", "entity_type", "occurred_at"],
    )

    # Add subscribed_events column to webhook_urls table
    op.add_column(
        "webhook_urls",
        sa.Column("subscribed_events", array_type, nullable=True),
    )


def downgrade():
    # Remove subscribed_events column from webhook_urls
    op.drop_column("webhook_urls", "subscribed_events")

    # Drop all indexes first
    op.drop_index("ix_event_log_entity", table_name="event_log")
    op.drop_index("ix_event_log_user_time", table_name="event_log")
    op.drop_index("ix_event_log_workspace_type_time", table_name="event_log")
    op.drop_index("ix_event_log_entity_type", table_name="event_log")
    op.drop_index("ix_event_log_entity_id", table_name="event_log")
    op.drop_index("ix_event_log_user_id", table_name="event_log")
    op.drop_index("ix_event_log_workspace_id", table_name="event_log")
    op.drop_index("ix_event_log_occurred_at", table_name="event_log")
    op.drop_index("ix_event_log_event_type", table_name="event_log")
    op.drop_index("ix_event_log_event_id", table_name="event_log")

    # Drop the event_log table
    op.drop_table("event_log")
