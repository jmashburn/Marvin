"""Create form_rate_limits table

Revision ID: create_form_rate_limits_table
Revises: create_form_submissions_table
Create Date: 2026-07-09 23:10:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def is_postgresql():
    """Check if the database is PostgreSQL."""
    return op.get_bind().dialect.name == "postgresql"


# revision identifiers, used by Alembic.
revision = "create_form_rate_limits_table"
down_revision = "create_form_submissions_table"
branch_labels = None
depends_on = None


def upgrade():
    use_pg = is_postgresql()
    uuid_type = UUID() if use_pg else sa.String(36)

    op.create_table(
        "form_rate_limits",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("form_id", uuid_type, nullable=False),
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


def downgrade():
    op.drop_table("form_rate_limits")
