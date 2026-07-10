"""add_forms_tables

Revision ID: 06fb009e9375
Revises: add_scheduled_tasks
Create Date: 2026-07-09 21:00:51.414630

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from marvin.db.migration_types import GUID

# revision identifiers, used by Alembic.
revision: str = "06fb009e9375"
down_revision: Union[str, None] = "69fec729cdb6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create forms table
    op.create_table(
        "forms",
        sa.Column("id", GUID, nullable=False),
        sa.Column("group_id", GUID, nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("schema_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("settings_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("submissions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_submission_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("update_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("group_id", "slug", name="uq_forms_group_slug"),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="chk_forms_status"),
    )
    op.create_index("ix_forms_group_id", "forms", ["group_id"])
    op.create_index("ix_forms_slug", "forms", ["slug"])
    op.create_index("ix_forms_group_status", "forms", ["group_id", "status"])

    # Create form_submissions table
    op.create_table(
        "form_submissions",
        sa.Column("id", GUID, nullable=False),
        sa.Column("form_id", GUID, nullable=False),
        sa.Column("group_id", GUID, nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="received"),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("referrer", sa.String(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("update_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('received', 'processed', 'failed')", name="chk_submissions_status"),
    )
    op.create_index("ix_form_submissions_form_id", "form_submissions", ["form_id"])
    op.create_index("ix_form_submissions_group_id", "form_submissions", ["group_id"])
    op.create_index("ix_form_submissions_submitted_at", "form_submissions", ["submitted_at"])
    op.create_index("ix_form_submissions_ip_address", "form_submissions", ["ip_address"])

    # Create form_rate_limits table
    op.create_table(
        "form_rate_limits",
        sa.Column("id", GUID, nullable=False),
        sa.Column("form_id", GUID, nullable=False),
        sa.Column("identifier", sa.String(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submission_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("update_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("form_id", "identifier", "window_start", name="uq_rate_limit_form_identifier_window"),
    )
    op.create_index("ix_form_rate_limits_form_id", "form_rate_limits", ["form_id"])
    op.create_index("ix_form_rate_limits_form_identifier", "form_rate_limits", ["form_id", "identifier"])
    op.create_index("ix_form_rate_limits_window_start", "form_rate_limits", ["window_start"])


def downgrade() -> None:
    op.drop_table("form_rate_limits")
    op.drop_table("form_submissions")
    op.drop_table("forms")
