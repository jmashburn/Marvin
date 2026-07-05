"""rename site_clients to api_clients

Revision ID: 6caab4aafc42
Revises: b39de631a423
Create Date: 2026-07-05 00:52:24.185794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '6caab4aafc42'
down_revision: Union[str, None] = 'b39de631a423'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename table
    op.rename_table('site_clients', 'api_clients')

    # Rename indexes
    with op.batch_alter_table('api_clients', schema=None) as batch_op:
        batch_op.drop_index('ix_site_clients_group_id')
        batch_op.drop_index('ix_site_clients_token_hash')
        batch_op.create_index('ix_api_clients_group_id', ['group_id'], unique=False)
        batch_op.create_index('ix_api_clients_token_hash', ['token_hash'], unique=True)

        # Rename is_active to enabled
        batch_op.alter_column('is_active', new_column_name='enabled')

        # Add description column
        batch_op.add_column(sa.Column('description', sa.String(), nullable=True))


def downgrade() -> None:
    # Reverse the changes
    with op.batch_alter_table('api_clients', schema=None) as batch_op:
        batch_op.drop_column('description')
        batch_op.alter_column('enabled', new_column_name='is_active')
        batch_op.drop_index('ix_api_clients_token_hash')
        batch_op.drop_index('ix_api_clients_group_id')
        batch_op.create_index('ix_site_clients_token_hash', ['token_hash'], unique=True)
        batch_op.create_index('ix_site_clients_group_id', ['group_id'], unique=False)

    op.rename_table('api_clients', 'site_clients')
