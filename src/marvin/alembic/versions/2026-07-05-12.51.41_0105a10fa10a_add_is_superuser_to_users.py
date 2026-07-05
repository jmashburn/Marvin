"""add_is_superuser_to_users

Revision ID: 0105a10fa10a
Revises: 4b869d573a78
Create Date: 2026-07-05 12:51:41.964916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '0105a10fa10a'
down_revision: Union[str, None] = '4b869d573a78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_superuser column to distinguish platform-level admins from workspace admins
    #
    # Admin model:
    # - is_superuser = True: Platform administrator (can manage all workspaces)
    # - admin = True, is_superuser = False: Workspace administrator (can manage their workspace)
    # - admin = False: Regular user
    #
    # Default to False for existing users - they remain workspace admins.
    # The default admin user will be promoted to superuser in the seed script.

    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'is_superuser')
