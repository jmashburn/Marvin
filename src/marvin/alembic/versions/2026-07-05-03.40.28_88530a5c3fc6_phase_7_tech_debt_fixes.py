"""phase 7 tech debt fixes

Revision ID: 88530a5c3fc6
Revises: ba8612ae5c08
Create Date: 2026-07-05 03:40:28.209724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '88530a5c3fc6'
down_revision: Union[str, None] = 'ba8612ae5c08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Phase 7 Tech Debt Fixes ###

    # 1. Add created_by column to entries if it doesn't exist
    #    (In Mealie fork this already existed, but for fresh installs it needs to be added)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('entries')]

    if 'created_by' not in columns:
        op.add_column('entries', sa.Column('created_by', marvin.db.migration_types.GUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))

    # Create index on created_by if it doesn't exist
    existing_entries_indexes = [idx['name'] for idx in inspector.get_indexes('entries')]
    if 'ix_entries_created_by' not in existing_entries_indexes:
        op.create_index(op.f('ix_entries_created_by'), 'entries', ['created_by'], unique=False)

    # 2. Add position to entry_resources table (may already exist from earlier migration)
    entry_resources_columns = [col['name'] for col in inspector.get_columns('entry_resources')]
    if 'position' not in entry_resources_columns:
        op.add_column('entry_resources', sa.Column('position', sa.Integer(), nullable=False, server_default='0'))

    # Create composite index if it doesn't exist (check existing indexes)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('entry_resources')]
    if 'ix_entry_resources_entry_id_position' not in existing_indexes:
        op.create_index('ix_entry_resources_entry_id_position', 'entry_resources', ['entry_id', 'position'], unique=False)

    # 3. Add url and external_id to resources table
    op.add_column('resources', sa.Column('url', sa.String(), nullable=True))
    op.add_column('resources', sa.Column('external_id', sa.String(), nullable=True))

    # 4. Add display fields to collections table
    op.add_column('collections', sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('collections', sa.Column('icon', sa.String(), nullable=True))
    op.add_column('collections', sa.Column('color', sa.String(), nullable=True))
    # ### end Phase 7 ###


def downgrade() -> None:
    # ### Phase 7 Tech Debt Fixes Rollback ###

    # 4. Remove collection display fields
    op.drop_column('collections', 'color')
    op.drop_column('collections', 'icon')
    op.drop_column('collections', 'sort_order')

    # 3. Remove resources external fields
    op.drop_column('resources', 'external_id')
    op.drop_column('resources', 'url')

    # 2. Remove entry_resources position
    op.drop_index(op.f('ix_entry_resources_entry_id_position'), table_name='entry_resources')
    op.drop_column('entry_resources', 'position')

    # 1. Remove entries created_by index (column already existed from Mealie)
    op.drop_index(op.f('ix_entries_created_by'), table_name='entries')
    # ### end Phase 7 ###
