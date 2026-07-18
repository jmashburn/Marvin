"""add output column to scheduled_task_execution_log

Stores the human-readable summary returned by task handlers so it appears
in the execution history rather than only in the application log.

Revision ID: e5f6a7b8c9da
Revises: 79503825a5e8
Create Date: 2026-07-16 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9da"
down_revision: Union[str, None] = "79503825a5e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("scheduled_task_execution_log") as batch_op:
        batch_op.add_column(sa.Column("output", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("scheduled_task_execution_log") as batch_op:
        batch_op.drop_column("output")
