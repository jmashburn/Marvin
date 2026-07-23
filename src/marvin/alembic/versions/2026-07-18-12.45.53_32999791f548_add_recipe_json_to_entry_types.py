"""add recipe_json to entry_types

Revision ID: 32999791f548
Revises: 65f53f89b701
Create Date: 2026-07-18 12:45:53.042399

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "32999791f548"
down_revision: str | None = "65f53f89b701"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("entry_types", sa.Column("recipe_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("entry_types", "recipe_json")
