"""add ai_executions table

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-17 10:30:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_executions",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("operation_slug", sa.String(), nullable=False),
        sa.Column("provider_type", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("triggered_by", marvin.db.migration_types.GUID(), nullable=True),
        sa.Column("trigger_type", sa.String(), nullable=False, server_default="api"),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", marvin.db.migration_types.GUID(), nullable=True),
        sa.Column("input_json", sa.JSON(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_executions_group_id", "ai_executions", ["group_id"])
    op.create_index("ix_ai_executions_operation_slug", "ai_executions", ["operation_slug"])
    op.create_index("ix_ai_executions_entity_id", "ai_executions", ["entity_id"])
    op.create_index("ix_ai_executions_group_created", "ai_executions", ["group_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_executions_group_created", table_name="ai_executions")
    op.drop_index("ix_ai_executions_entity_id", table_name="ai_executions")
    op.drop_index("ix_ai_executions_operation_slug", table_name="ai_executions")
    op.drop_index("ix_ai_executions_group_id", table_name="ai_executions")
    op.drop_table("ai_executions")
