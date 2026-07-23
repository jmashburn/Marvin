"""add headers_json to webhook_urls

Stores custom HTTP headers for webhook requests. Header values support
{{SLUG}} secret interpolation resolved at fire time.

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-07-15 00:00:02.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a8"
down_revision: str | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("webhook_urls") as batch_op:
        batch_op.add_column(sa.Column("headers_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("webhook_urls") as batch_op:
        batch_op.drop_column("headers_json")
