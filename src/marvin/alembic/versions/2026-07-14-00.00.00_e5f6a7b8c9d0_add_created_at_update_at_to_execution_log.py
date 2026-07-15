"""add created_at and update_at to scheduled_task_execution_log

SqlAlchemyBase declares created_at / update_at on all models but the initial
migration omitted them from scheduled_task_execution_log.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("scheduled_task_execution_log") as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("update_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("scheduled_task_execution_log") as batch_op:
        batch_op.drop_column("update_at")
        batch_op.drop_column("created_at")
