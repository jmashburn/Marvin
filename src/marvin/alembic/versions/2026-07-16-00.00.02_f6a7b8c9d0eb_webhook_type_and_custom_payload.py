"""webhook_type enum expansion and custom_payload column

Switches webhook_type from EventDocumentType to WebhookMode (adds 'entries'
and 'event_driven' values) and adds custom_payload JSON column.
Existing 'generic' and 'user' values remain valid.

Revision ID: f6a7b8c9d0eb
Revises: e5f6a7b8c9da
Create Date: 2026-07-16 00:00:02.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0eb"
down_revision: str | None = "e5f6a7b8c9da"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    old_enum = sa.Enum("generic", "user", name="eventdocumenttype")
    new_enum = sa.Enum("generic", "user", "entries", "event_driven", name="webhookmode")
    op.add_column("webhook_urls", sa.Column("custom_payload", sa.JSON(), nullable=True))
    if bind.dialect.name == "postgresql":
        # Postgres enums are real types: create the new one, then cast the column into it (text
        # bridge handles the cross-enum change). Postgres can ALTER COLUMN directly.
        new_enum.create(bind, checkfirst=True)
        op.alter_column(
            "webhook_urls",
            "webhook_type",
            existing_type=old_enum,
            type_=new_enum,
            existing_nullable=True,
            postgresql_using="webhook_type::text::webhookmode",
        )
        op.alter_column("webhook_urls", "scheduled_time", existing_type=sa.DateTime(timezone=True), nullable=True)
    else:
        # SQLite cannot ALTER COLUMN outside batch mode — both changes must ride the table rebuild.
        with op.batch_alter_table("webhook_urls") as batch_op:
            batch_op.alter_column(
                "webhook_type",
                existing_type=old_enum,
                type_=new_enum,
                existing_nullable=True,
            )
            batch_op.alter_column("scheduled_time", existing_type=sa.DateTime(timezone=True), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("webhook_urls") as batch_op:
        batch_op.drop_column("custom_payload")
        batch_op.alter_column(
            "webhook_type",
            existing_type=sa.Enum("generic", "user", "entries", "event_driven", name="webhookmode"),
            type_=sa.Enum("generic", "user", name="eventdocumenttype"),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "scheduled_time",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
