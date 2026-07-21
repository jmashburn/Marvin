"""add integrations table

Revision ID: 024ede5589c6
Revises: 326a21762c79
Create Date: 2026-07-21 15:14:45.966901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '024ede5589c6'
down_revision: Union[str, None] = '326a21762c79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only the integrations table — unrelated datetime/constraint drift that autogenerate
    # also surfaced was stripped out; it is not part of this change.
    op.create_table('integrations',
    sa.Column('id', marvin.db.migration_types.GUID(), nullable=False),
    sa.Column('group_id', marvin.db.migration_types.GUID(), nullable=False),
    sa.Column('provider', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('config', sa.JSON(), nullable=True),
    sa.Column('secret_ref', sa.String(), nullable=True),
    sa.Column('status', sa.String(), server_default='unconfigured', nullable=False),
    sa.Column('last_checked_at', sa.DateTime(), nullable=True),
    sa.Column('last_error', sa.String(), nullable=True),
    sa.Column('created_at', marvin.db.migration_types.NaiveDateTime(), nullable=True),
    sa.Column('update_at', marvin.db.migration_types.NaiveDateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('group_id', 'slug', name='uq_integrations_group_slug')
    )
    op.create_index(op.f('ix_integrations_group_id'), 'integrations', ['group_id'], unique=False)
    op.create_index(op.f('ix_integrations_provider'), 'integrations', ['provider'], unique=False)
    op.create_index(op.f('ix_integrations_slug'), 'integrations', ['slug'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_integrations_slug'), table_name='integrations')
    op.drop_index(op.f('ix_integrations_provider'), table_name='integrations')
    op.drop_index(op.f('ix_integrations_group_id'), table_name='integrations')
    op.drop_table('integrations')
