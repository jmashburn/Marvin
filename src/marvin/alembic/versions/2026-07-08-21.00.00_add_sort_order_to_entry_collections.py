"""add sort_order and timestamps to entry_collections

Revision ID: add_sort_order_ec
Revises: add_event_log_and_webhook_subscriptions
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

    # Add timestamps
    op.add_column("entry_collections", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("NOW()")))
    op.add_column("entry_collections", sa.Column("update_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove timestamps
    op.drop_column("entry_collections", "update_at")
    op.drop_column("entry_collections", "created_at")

    # Rename back to 'position'
    op.alter_column("entry_collections", "sort_order", new_column_name="position")
