"""add automation execution records

Revision ID: f0382e299d4e
Revises: e44490e23dbc
Create Date: 2026-07-20 01:54:48.034604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = 'f0382e299d4e'
down_revision: Union[str, None] = 'e44490e23dbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "automation_executions",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("automation_id", marvin.db.migration_types.GUID(), nullable=True),
        sa.Column("automation_slug", sa.String(), nullable=False),
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("targets_matched", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("targets_run", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("capped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("steps_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("steps_ok", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("steps_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("definition_snapshot", sa.JSON(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("triggered_by", marvin.db.migration_types.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["automation_id"], ["workspace_automations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_executions_group_id", "automation_executions", ["group_id"])
    op.create_index("ix_automation_executions_automation_id", "automation_executions", ["automation_id"])
    op.create_index("ix_automation_executions_correlation_id", "automation_executions", ["correlation_id"])

    op.create_table(
        "automation_action_executions",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("execution_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("target_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_entity_type", sa.String(), nullable=True),
        sa.Column("target_entity_id", sa.String(), nullable=True),
        sa.Column("action_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("output_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["execution_id"], ["automation_executions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_action_executions_execution_id", "automation_action_executions", ["execution_id"])
    op.create_index("ix_automation_action_executions_group_id", "automation_action_executions", ["group_id"])


def downgrade() -> None:
    op.drop_index("ix_automation_action_executions_group_id", table_name="automation_action_executions")
    op.drop_index("ix_automation_action_executions_execution_id", table_name="automation_action_executions")
    op.drop_table("automation_action_executions")
    op.drop_index("ix_automation_executions_correlation_id", table_name="automation_executions")
    op.drop_index("ix_automation_executions_automation_id", table_name="automation_executions")
    op.drop_index("ix_automation_executions_group_id", table_name="automation_executions")
    op.drop_table("automation_executions")
