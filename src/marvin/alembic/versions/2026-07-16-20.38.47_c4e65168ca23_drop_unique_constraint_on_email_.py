"""drop unique constraint on email_templates template_type group_id

Revision ID: c4e65168ca23
Revises: a9b0c1d2e3f4
Create Date: 2026-07-16 20:38:47.409201

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e65168ca23"
down_revision: str | None = "278ea16934c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("email_templates") as batch_op:
        batch_op.drop_constraint("uq_email_template_type_group", type_="unique")


def downgrade() -> None:
    with op.batch_alter_table("email_templates") as batch_op:
        batch_op.create_unique_constraint(
            "uq_email_template_type_group",
            ["template_type", "group_id"],
        )
