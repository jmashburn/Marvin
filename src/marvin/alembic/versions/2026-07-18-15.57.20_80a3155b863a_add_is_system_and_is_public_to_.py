"""add is_system and is_public to collections

Revision ID: 80a3155b863a
Revises: 32999791f548
Create Date: 2026-07-18 15:57:20.894006

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '80a3155b863a'
down_revision: Union[str, None] = '32999791f548'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # is_system: seeded workflow collections (Inbox/Drafts/…) that are locked from edit/delete.
    op.add_column(
        "collections",
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # is_public: whether the collection is exposed via the publish API. Workflow collections
    # are internal (is_public=False); everything else defaults to public.
    op.add_column(
        "collections",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("collections", "is_public")
    op.drop_column("collections", "is_system")
