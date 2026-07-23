"""simplify email_templates drop structured fields add body_markdown

Revision ID: 278ea16934c3
Revises: 619ee8a76d4f
Create Date: 2026-07-16 20:11:35.858989

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "278ea16934c3"
down_revision: str | None = "619ee8a76d4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add body_markdown column
    op.add_column("email_templates", sa.Column("body_markdown", sa.Text(), nullable=True))

    # Migrate existing content: concatenate structured fields into body_markdown.
    # Use two literal newline chars in the SQL string (portable) rather than char(10) — that's a
    # SQLite function; Postgres spells it chr(10) and reads bare `char(...)` as a type.
    nl = chr(10)
    op.execute(
        "UPDATE email_templates "
        "SET body_markdown = COALESCE(message_top, '') || "
        "    CASE WHEN message_bottom IS NOT NULL AND message_bottom != '' "
        f"         THEN '{nl}{nl}' || message_bottom "
        "         ELSE '' END "
        "WHERE message_top IS NOT NULL OR message_bottom IS NOT NULL"
    )

    # Drop the structured content columns
    with op.batch_alter_table("email_templates") as batch_op:
        batch_op.drop_column("header_text")
        batch_op.drop_column("message_top")
        batch_op.drop_column("message_bottom")
        batch_op.drop_column("button_text")


def downgrade() -> None:
    with op.batch_alter_table("email_templates") as batch_op:
        batch_op.add_column(sa.Column("button_text", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("message_bottom", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("message_top", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("header_text", sa.String(), nullable=True))

    # Restore message_top from body_markdown on downgrade
    op.execute("""
        UPDATE email_templates
        SET message_top = body_markdown
        WHERE body_markdown IS NOT NULL
    """)

    with op.batch_alter_table("email_templates") as batch_op:
        batch_op.drop_column("body_markdown")
