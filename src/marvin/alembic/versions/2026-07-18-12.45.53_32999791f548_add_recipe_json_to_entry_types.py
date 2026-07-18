"""add recipe_json to entry_types

Revision ID: 32999791f548
Revises: 65f53f89b701
Create Date: 2026-07-18 12:45:53.042399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '32999791f548'
down_revision: Union[str, None] = '65f53f89b701'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("entry_types", sa.Column("recipe_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("entry_types", "recipe_json")
