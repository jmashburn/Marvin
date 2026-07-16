"""webhook_type enum expansion and custom_payload column

Switches webhook_type from EventDocumentType to WebhookMode (adds 'entries'
and 'event_driven' values) and adds custom_payload JSON column.
Existing 'generic' and 'user' values remain valid.

Revision ID: f6a7b8c9d0eb
Revises: e5f6a7b8c9da
Create Date: 2026-07-16 00:00:02.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0eb"
down_revision: Union[str, None] = "e5f6a7b8c9da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("webhook_urls") as batch_op:
        batch_op.add_column(sa.Column("custom_payload", sa.JSON(), nullable=True))
        # Recreate webhook_type with the new WebhookMode enum values.
        # SQLite stores enum values as strings so existing 'generic'/'user' rows
        # are automatically valid under the new enum.
        batch_op.alter_column(
            "webhook_type",
            existing_type=sa.Enum("generic", "user", name="eventdocumenttype"),
            type_=sa.Enum("generic", "user", "entries", "event_driven", name="webhookmode"),
            existing_nullable=True,
        )
        # Make scheduled_time nullable (event_driven webhooks have no schedule).
        batch_op.alter_column(
            "scheduled_time",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )


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
