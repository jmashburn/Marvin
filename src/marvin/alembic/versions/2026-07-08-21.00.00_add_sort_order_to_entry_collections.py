"""rename position to sort_order in entry_collections

Revision ID: add_sort_order_ec
Revises: b5c9d3f2e4a7
Create Date: 2026-07-08 21:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_sort_order_ec"
down_revision = "b5c9d3f2e4a7"
branch_labels = None
depends_on = None


def upgrade():
    # Rename 'position' column to 'sort_order'
    op.alter_column("entry_collections", "position", new_column_name="sort_order")


def downgrade():
    # Rename back to 'position'
    op.alter_column("entry_collections", "sort_order", new_column_name="position")
