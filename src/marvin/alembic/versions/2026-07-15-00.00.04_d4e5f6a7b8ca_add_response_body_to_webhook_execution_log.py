"""add response_body to webhook_execution_logs

Captures the HTTP response body on failed webhook calls for debugging.

Revision ID: d4e5f6a7b8ca
Revises: c3d4e5f6a7b9
Create Date: 2026-07-15 00:00:04.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8ca"
down_revision: str | None = "c3d4e5f6a7b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("webhook_execution_logs") as batch_op:
        batch_op.add_column(sa.Column("response_body", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("webhook_execution_logs") as batch_op:
        batch_op.drop_column("response_body")
