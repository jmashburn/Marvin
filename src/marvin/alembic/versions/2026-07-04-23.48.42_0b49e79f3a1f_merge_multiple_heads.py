"""merge multiple heads

Revision ID: 0b49e79f3a1f
Revises: 8a1b2c3d4e5f, 0afdb6d41fa1
Create Date: 2026-07-04 23:48:42.573303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '0b49e79f3a1f'
down_revision: Union[str, None] = ('8a1b2c3d4e5f', '0afdb6d41fa1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
