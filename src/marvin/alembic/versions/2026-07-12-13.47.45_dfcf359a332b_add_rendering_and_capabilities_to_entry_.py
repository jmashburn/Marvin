"""add rendering and capabilities to entry_types

Revision ID: dfcf359a332b
Revises: d1d2bc0fed86
Create Date: 2026-07-12 13:47:45.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "dfcf359a332b"
down_revision: Union[str, None] = "d1d2bc0fed86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("entry_types", sa.Column("rendering_json", sa.JSON(), nullable=True))
    op.add_column("entry_types", sa.Column("capabilities_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("entry_types", "capabilities_json")
    op.drop_column("entry_types", "rendering_json")
