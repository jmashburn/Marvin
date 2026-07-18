"""add suggestion_json to entries

Revision ID: a112d0c60cb7
Revises: 80a3155b863a
Create Date: 2026-07-18 17:39:00.466395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = 'a112d0c60cb7'
down_revision: Union[str, None] = '80a3155b863a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pending AI-proposed changes staged for human review, keyed by target field
    # (e.g. {"summary": "...", "_meta": {...}}). Applied via the apply-suggestion endpoint.
    op.add_column("entries", sa.Column("suggestion_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("entries", "suggestion_json")
