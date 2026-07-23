"""add suggestion_json to entries

Revision ID: a112d0c60cb7
Revises: 80a3155b863a
Create Date: 2026-07-18 17:39:00.466395

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a112d0c60cb7"
down_revision: str | None = "80a3155b863a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Pending AI-proposed changes staged for human review, keyed by target field
    # (e.g. {"summary": "...", "_meta": {...}}). Applied via the apply-suggestion endpoint.
    op.add_column("entries", sa.Column("suggestion_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("entries", "suggestion_json")
