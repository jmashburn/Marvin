"""create_notification_execution_logs

Revision ID: 619ee8a76d4f
Revises: f6a7b8c9d0eb
Create Date: 2026-07-16 00:00:03.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
import marvin.db.migration_types

revision: str = "619ee8a76d4f"
down_revision: Union[str, None] = "f6a7b8c9d0eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_execution_logs",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("notifier_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["notifier_id"], ["group_events_notifiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_execution_logs_notifier_id", "notification_execution_logs", ["notifier_id"])
    op.create_index("ix_notification_execution_logs_group_id", "notification_execution_logs", ["group_id"])
    op.create_index("ix_notification_execution_logs_executed_at", "notification_execution_logs", ["executed_at"])
    op.create_index("ix_notification_execution_logs_event_type", "notification_execution_logs", ["event_type"])
    op.create_index("ix_notification_execution_logs_status", "notification_execution_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_notification_execution_logs_status", table_name="notification_execution_logs")
    op.drop_index("ix_notification_execution_logs_event_type", table_name="notification_execution_logs")
    op.drop_index("ix_notification_execution_logs_executed_at", table_name="notification_execution_logs")
    op.drop_index("ix_notification_execution_logs_group_id", table_name="notification_execution_logs")
    op.drop_index("ix_notification_execution_logs_notifier_id", table_name="notification_execution_logs")
    op.drop_table("notification_execution_logs")
