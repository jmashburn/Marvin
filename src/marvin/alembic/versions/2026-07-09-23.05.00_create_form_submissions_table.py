"""Create form_submissions table

Revision ID: create_form_submissions_table
Revises: create_forms_table
Create Date: 2026-07-09 23:05:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID


def is_postgresql():
    """Check if the database is PostgreSQL."""
    return op.get_bind().dialect.name == "postgresql"


# revision identifiers, used by Alembic.
revision = "create_form_submissions_table"
down_revision = "create_forms_table"
branch_labels = None
depends_on = None


def upgrade():
    use_pg = is_postgresql()
    uuid_type = UUID() if use_pg else sa.String(36)
    jsonb_type = JSONB() if use_pg else sa.JSON()
    inet_type = INET() if use_pg else sa.String()

    op.create_table(
        "form_submissions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("form_id", uuid_type, nullable=False),
        sa.Column("group_id", uuid_type, nullable=False),
        sa.Column("data_json", jsonb_type, nullable=False, server_default="{}"),
        sa.Column("metadata_json", jsonb_type, nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="received"),
        sa.Column("ip_address", inet_type, nullable=True),
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


def downgrade():
    op.drop_table("form_submissions")
