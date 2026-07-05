"""webhook_datetime_and_logging

Revision ID: 0afdb6d41fa1
Revises: 096bd305c0d2
Create Date: 2026-06-05 15:20:50.116379

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = "0afdb6d41fa1"
down_revision: Union[str, None] = "096bd305c0d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create the webhook_execution_logs table
    op.create_table(
        "webhook_execution_logs",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("webhook_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["webhook_id"], ["webhook_urls.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_execution_logs_webhook_id", "webhook_execution_logs", ["webhook_id"])
    op.create_index("ix_webhook_execution_logs_status", "webhook_execution_logs", ["status"])
    op.create_index("ix_webhook_execution_logs_executed_at", "webhook_execution_logs", ["executed_at"])

    # Step 2: Create a temporary column for the new datetime type
    op.add_column("webhook_urls", sa.Column("scheduled_time_new", sa.DateTime(timezone=True), nullable=True))

    # Step 3: Migrate data from TIME to DATETIME (preserving time, using current date in UTC)
    # This SQL will convert existing TIME values to DATETIME by combining with current date
    op.execute("""
        UPDATE webhook_urls
        SET scheduled_time_new = (CURRENT_DATE || ' ' || scheduled_time::text)::timestamp AT TIME ZONE 'UTC'
        WHERE scheduled_time IS NOT NULL
    """)

    # Step 4: Drop the old scheduled_time column
    op.drop_column("webhook_urls", "scheduled_time")

    # Step 5: Rename the new column to scheduled_time
    op.alter_column("webhook_urls", "scheduled_time_new", new_column_name="scheduled_time")

    # Step 6: Create index for optimized scheduling queries
    op.create_index("ix_webhook_urls_enabled_scheduled", "webhook_urls", ["enabled", "scheduled_time"])


def downgrade() -> None:
    # Step 1: Drop the composite index
    op.drop_index("ix_webhook_urls_enabled_scheduled", table_name="webhook_urls")

    # Step 2: Create a temporary column for the old time type
    op.add_column("webhook_urls", sa.Column("scheduled_time_old", sa.Time(), nullable=True))

    # Step 3: Migrate data from DATETIME back to TIME (extracting just the time component)
    op.execute("""
        UPDATE webhook_urls
        SET scheduled_time_old = scheduled_time::time
        WHERE scheduled_time IS NOT NULL
    """)

    # Step 4: Drop the datetime column
    op.drop_column("webhook_urls", "scheduled_time")

    # Step 5: Rename the old column back to scheduled_time
    op.alter_column("webhook_urls", "scheduled_time_old", new_column_name="scheduled_time")

    # Step 6: Drop execution logs table and its indexes (cascade handles foreign keys)
    op.drop_index("ix_webhook_execution_logs_executed_at", table_name="webhook_execution_logs")
    op.drop_index("ix_webhook_execution_logs_status", table_name="webhook_execution_logs")
    op.drop_index("ix_webhook_execution_logs_webhook_id", table_name="webhook_execution_logs")
    op.drop_table("webhook_execution_logs")
