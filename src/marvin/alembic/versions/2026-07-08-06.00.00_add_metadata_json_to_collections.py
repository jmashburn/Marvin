"""Add metadata_json to collections

Revision ID: a3f8e9c4d2b1
Revises: d1d2bc0fed86
Create Date: 2026-07-08 06:00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a3f8e9c4d2b1"
down_revision = "d1d2bc0fed86"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("collections", sa.Column("metadata_json", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("collections", "metadata_json")
