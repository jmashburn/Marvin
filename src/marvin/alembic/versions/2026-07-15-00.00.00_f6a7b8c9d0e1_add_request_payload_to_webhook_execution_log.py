"""add request_payload to webhook_execution_logs

Stores the JSON payload sent to the webhook endpoint for debugging/auditing.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("webhook_execution_logs") as batch_op:
        batch_op.add_column(sa.Column("request_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("webhook_execution_logs") as batch_op:
        batch_op.drop_column("request_payload")
