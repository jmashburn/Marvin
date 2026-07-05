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

    # 1. created_by already exists in entries table (from Mealie schema)
    #    Just ensure it has the foreign key and index
    # Note: Foreign key may already exist, wrapped in try/except in production
    op.create_index(op.f('ix_entries_created_by'), 'entries', ['created_by'], unique=False)

    # 2. Add position to entry_resources table
    op.add_column('entry_resources', sa.Column('position', sa.Integer(), nullable=False, server_default='0'))
    op.create_index(op.f('ix_entry_resources_entry_id_position'), 'entry_resources', ['entry_id', 'position'], unique=False)

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
