"""add_role_based_authorization

Revision ID: 3dd1c8a4ed25
Revises: 0105a10fa10a
Create Date: 2026-07-05 13:03:55.005180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '3dd1c8a4ed25'
down_revision: Union[str, None] = '0105a10fa10a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 1: Add platform_role column to users table
    # Migrate existing is_superuser values
    op.add_column('users', sa.Column('platform_role', sa.String(), nullable=False, server_default='NONE'))

    # Migrate existing is_superuser=True users to SUPER_ADMIN platform role
    op.execute("UPDATE users SET platform_role = 'SUPER_ADMIN' WHERE is_superuser = 1")

    # Phase 2: Create workspace_members junction table
    # This replaces the single group_id on users with a many-to-many relationship
    op.create_table(
        'workspace_members',
        sa.Column('id', marvin.db.migration_types.GUID(), nullable=False),
        sa.Column('user_id', marvin.db.migration_types.GUID(), nullable=False),
        sa.Column('group_id', marvin.db.migration_types.GUID(), nullable=False),
        sa.Column('workspace_role', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('update_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'group_id', name='uq_workspace_member'),
    )
    op.create_index(op.f('ix_workspace_members_user_id'), 'workspace_members', ['user_id'], unique=False)
    op.create_index(op.f('ix_workspace_members_group_id'), 'workspace_members', ['group_id'], unique=False)

    # Phase 3: Migrate existing user-group memberships to workspace_members
    # Users with admin=True become ADMIN, others become AUTHOR
    # This is a safe default - workspace owners can adjust roles after migration
    op.execute("""
        INSERT INTO workspace_members (id, user_id, group_id, workspace_role, created_at, update_at)
        SELECT
            lower(hex(randomblob(16))) as id,
            users.id as user_id,
            users.group_id as group_id,
            CASE
                WHEN users.admin = 1 THEN 'ADMIN'
                ELSE 'AUTHOR'
            END as workspace_role,
            datetime('now') as created_at,
            datetime('now') as update_at
        FROM users
        WHERE users.group_id IS NOT NULL
    """)

    # Note: We keep users.group_id for now to maintain backward compatibility
    # Future migration can remove it once all code uses workspace_members


def downgrade() -> None:
    # Remove workspace_members table
    op.drop_index(op.f('ix_workspace_members_group_id'), table_name='workspace_members')
    op.drop_index(op.f('ix_workspace_members_user_id'), table_name='workspace_members')
    op.drop_table('workspace_members')

    # Remove platform_role column
    op.drop_column('users', 'platform_role')
