"""add workspace smtp profiles

Revision ID: 326a21762c79
Revises: ae76953cdc37
Create Date: 2026-07-21 14:06:41.192988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '326a21762c79'
down_revision: Union[str, None] = 'ae76953cdc37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workspace_smtp_profiles',
        sa.Column('id', marvin.db.migration_types.GUID(), nullable=False),
        sa.Column('group_id', marvin.db.migration_types.GUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('host', sa.String(), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('password_encrypted', sa.Text(), nullable=True),
        sa.Column('from_name', sa.String(), nullable=True),
        sa.Column('from_email', sa.String(), nullable=True),
        sa.Column('auth_strategy', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', marvin.db.migration_types.NaiveDateTime(), nullable=True),
        sa.Column('update_at', marvin.db.migration_types.NaiveDateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_workspace_smtp_profiles_group_id', 'workspace_smtp_profiles', ['group_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_workspace_smtp_profiles_group_id', table_name='workspace_smtp_profiles')
    op.drop_table('workspace_smtp_profiles')
