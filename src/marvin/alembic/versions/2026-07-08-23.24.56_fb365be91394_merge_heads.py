"""merge_heads

Revision ID: fb365be91394
Revises: add_scheduled_tasks, 0def306c2354
Create Date: 2026-07-08 23:24:56.090390

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = "fb365be91394"
down_revision: Union[str, None] = ("add_scheduled_tasks", "0def306c2354")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
