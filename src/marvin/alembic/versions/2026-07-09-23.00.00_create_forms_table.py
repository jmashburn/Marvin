"""Create forms table

Revision ID: create_forms_table
Revises: add_scheduled_tasks
Create Date: 2026-07-09 23:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


def is_postgresql():
    """Check if the database is PostgreSQL."""
    return op.get_bind().dialect.name == "postgresql"


# revision identifiers, used by Alembic.
revision = "create_forms_table"
down_revision = "add_scheduled_tasks"
branch_labels = None
depends_on = None


def upgrade():
    use_pg = is_postgresql()
    uuid_type = UUID() if use_pg else sa.String(36)
    jsonb_type = JSONB() if use_pg else sa.JSON()

    op.create_table(
        "forms",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("group_id", uuid_type, nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("schema_json", jsonb_type, nullable=False, server_default="{}"),
        sa.Column("settings_json", jsonb_type, nullable=True),
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


def downgrade():
    op.drop_table("forms")
