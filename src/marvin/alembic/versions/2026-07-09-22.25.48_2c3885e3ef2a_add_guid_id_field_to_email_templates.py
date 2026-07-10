"""add GUID id field to email_templates

Revision ID: 2c3885e3ef2a
Revises: 9423fc4291e1
Create Date: 2026-07-09 22:25:48.573706

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = "2c3885e3ef2a"
down_revision: Union[str, None] = "9423fc4291e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop and recreate table with correct GUID id field
    op.drop_table("email_templates")
    op.create_table(
        "email_templates",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("template_type", sa.String(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("header_text", sa.String(), nullable=True),
        sa.Column("message_top", sa.Text(), nullable=True),
        sa.Column("message_bottom", sa.Text(), nullable=True),
        sa.Column("button_text", sa.String(), nullable=True),
        sa.Column("custom_html", sa.Text(), nullable=True),
        sa.Column("available_variables", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_type", "group_id", name="uq_email_template_type_group"),
    )
    op.create_index(op.f("ix_email_templates_group_id"), "email_templates", ["group_id"], unique=False)
    op.create_index(op.f("ix_email_templates_template_type"), "email_templates", ["template_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_templates_template_type"), table_name="email_templates")
    op.drop_index(op.f("ix_email_templates_group_id"), table_name="email_templates")
    op.drop_table("email_templates")
