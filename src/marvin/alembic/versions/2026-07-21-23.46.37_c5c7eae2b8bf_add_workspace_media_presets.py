"""add workspace media presets

Revision ID: c5c7eae2b8bf
Revises: 058ffb19e2bb
Create Date: 2026-07-21 23:46:37.925275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c5c7eae2b8bf'
down_revision: Union[str, None] = '058ffb19e2bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-workspace grade preset overrides ({name: {warmth, contrast, ...}}), merged over the
    # built-in GRADE_PRESETS. Nullable → no behaviour change until a workspace sets it.
    with op.batch_alter_table('workspace_ai_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('media_presets', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('workspace_ai_settings', schema=None) as batch_op:
        batch_op.drop_column('media_presets')
