"""add ai persona fields

Revision ID: b1dbbd08d7fd
Revises: ee87dac68e39
Create Date: 2026-07-19 21:24:48.116012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = 'b1dbbd08d7fd'
down_revision: Union[str, None] = 'ee87dac68e39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workspace_ai_settings", sa.Column("assistant_name", sa.String(), nullable=True))
    op.add_column("workspace_ai_settings", sa.Column("persona_prompt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("workspace_ai_settings", "persona_prompt")
    op.drop_column("workspace_ai_settings", "assistant_name")
