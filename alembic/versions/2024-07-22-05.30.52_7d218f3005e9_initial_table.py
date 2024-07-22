"""Initial Table

Revision ID: 7d218f3005e9
Revises:
Create Date: 2024-07-22 05:30:52.222182

"""

from typing import Sequence, Union

import marvin.db.migration_types
from alembic import op
import sqlalchemy as sa
from sqlalchemy import engine_from_config


# revision identifiers, used by Alembic.
revision: str = "7d218f3005e9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table, schema=None):
    config = op.get_context().config
    engine = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.")
    insp = sa.inspect(engine)
    return insp.has_table(table, schema)


def upgrade() -> None:
    if table_exists("user"):
        return

    op.create_table(
        "groups",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_index()
