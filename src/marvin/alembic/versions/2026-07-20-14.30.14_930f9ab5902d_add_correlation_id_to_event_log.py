"""add correlation_id to event_log

Revision ID: 930f9ab5902d
Revises: b7e4430df8eb
Create Date: 2026-07-20 14:30:14.131752

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "930f9ab5902d"
down_revision: str | None = "b7e4430df8eb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("event_log", schema=None) as batch_op:
        batch_op.add_column(sa.Column("correlation_id", sa.String(), nullable=True))
        batch_op.create_index("ix_event_log_correlation_id", ["correlation_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("event_log", schema=None) as batch_op:
        batch_op.drop_index("ix_event_log_correlation_id")
        batch_op.drop_column("correlation_id")
