"""add_active_workspace_tracking

Revision ID: d8568bbaca53
Revises: 3dd1c8a4ed25
Create Date: 2026-07-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = 'd8568bbaca53'
down_revision: Union[str, None] = '3dd1c8a4ed25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add active_group_id column to users table
    # This tracks which workspace the user is currently working in
    # Falls back to group_id if NULL (backward compatibility)
    op.add_column('users',
        sa.Column('active_group_id', marvin.db.migration_types.GUID(), nullable=True)
    )

    # Add foreign key constraint with SET NULL on delete
    # If a workspace is deleted, user's active workspace resets to NULL
    op.create_foreign_key(
        'fk_users_active_group_id',
        'users', 'groups',
        ['active_group_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add index for performance
    op.create_index('ix_users_active_group_id', 'users', ['active_group_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_users_active_group_id', table_name='users')
    op.drop_constraint('fk_users_active_group_id', 'users', type_='foreignkey')
    op.drop_column('users', 'active_group_id')
