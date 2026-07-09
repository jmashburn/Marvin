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
    # Check if we need to rename 'position' to 'sort_order'
    # If position doesn't exist, the table might have been created with sort_order already
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("entry_collections")]

    if "position" in columns and "sort_order" not in columns:
        # Rename 'position' column to 'sort_order'
        op.alter_column("entry_collections", "position", new_column_name="sort_order")
    elif "sort_order" in columns:
        # sort_order already exists, nothing to do
        pass
    else:
        # Neither exists, add sort_order
        op.add_column("entry_collections", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    # Check if sort_order exists before trying to rename
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns("entry_collections")]

    if "sort_order" in columns:
        op.alter_column("entry_collections", "sort_order", new_column_name="position")
