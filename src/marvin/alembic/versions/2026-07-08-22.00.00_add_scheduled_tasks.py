"""Add scheduled_tasks and scheduled_task_execution_log tables

Revision ID: add_scheduled_tasks
Revises: add_sort_order_ec
Create Date: 2026-07-08 22:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# Determine if we're using PostgreSQL
def is_postgresql():
    """Check if the database is PostgreSQL."""
    return op.get_bind().dialect.name == "postgresql"


# revision identifiers, used by Alembic.
revision = "add_scheduled_tasks"
down_revision = "add_sort_order_ec"
branch_labels = None
depends_on = None


def upgrade():
    # Determine column types based on database
    use_pg = is_postgresql()
    uuid_type = UUID() if use_pg else sa.String(36)
    json_type = JSONB() if use_pg else sa.JSON()

    # Create scheduled_tasks table
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("group_id", uuid_type, nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("schedule_type", sa.String(), nullable=False),
        sa.Column("schedule_config", json_type, nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(), nullable=True),
        sa.Column("last_duration_ms", sa.Integer(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("task_config", json_type, nullable=False, server_default="{}"),
        sa.Column("retry_policy", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("update_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("group_id", "slug", name="uq_scheduled_tasks_group_slug"),
    )

    # Create indexes for scheduled_tasks
    op.create_index("ix_scheduled_tasks_group_id", "scheduled_tasks", ["group_id"])
    op.create_index("ix_scheduled_tasks_next_run_at", "scheduled_tasks", ["next_run_at"])
    op.create_index("ix_scheduled_tasks_task_type", "scheduled_tasks", ["task_type"])
    op.create_index("ix_scheduled_tasks_next_run", "scheduled_tasks", ["next_run_at", "enabled"])
    op.create_index("ix_scheduled_tasks_workspace", "scheduled_tasks", ["group_id", "enabled"])

    # Create scheduled_task_execution_log table
    op.create_table(
        "scheduled_task_execution_log",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("task_id", uuid_type, nullable=False),
        sa.Column("group_id", uuid_type, nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_traceback", sa.Text(), nullable=True),
        sa.Column("retry_attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["scheduled_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
    )

    # Create indexes for scheduled_task_execution_log
    op.create_index("ix_task_execution_log_task_id", "scheduled_task_execution_log", ["task_id"])
    op.create_index("ix_task_execution_log_group_id", "scheduled_task_execution_log", ["group_id"])
    op.create_index("ix_task_execution_log_executed_at", "scheduled_task_execution_log", ["executed_at"])
    op.create_index("ix_task_execution_task_time", "scheduled_task_execution_log", ["task_id", "executed_at"])
    op.create_index("ix_task_execution_workspace_time", "scheduled_task_execution_log", ["group_id", "executed_at"])


def downgrade():
    # Drop indexes for scheduled_task_execution_log
    op.drop_index("ix_task_execution_workspace_time", table_name="scheduled_task_execution_log")
    op.drop_index("ix_task_execution_task_time", table_name="scheduled_task_execution_log")
    op.drop_index("ix_task_execution_log_executed_at", table_name="scheduled_task_execution_log")
    op.drop_index("ix_task_execution_log_group_id", table_name="scheduled_task_execution_log")
    op.drop_index("ix_task_execution_log_task_id", table_name="scheduled_task_execution_log")

    # Drop scheduled_task_execution_log table
    op.drop_table("scheduled_task_execution_log")

    # Drop indexes for scheduled_tasks
    op.drop_index("ix_scheduled_tasks_workspace", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_next_run", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_task_type", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_next_run_at", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_group_id", table_name="scheduled_tasks")

    # Drop scheduled_tasks table
    op.drop_table("scheduled_tasks")
