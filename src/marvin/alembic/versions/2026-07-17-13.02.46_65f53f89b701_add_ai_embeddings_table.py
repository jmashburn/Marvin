"""add ai_embeddings table

Revision ID: 65f53f89b701
Revises: c2d3e4f5a6b7
Create Date: 2026-07-17 13:02:46.767199

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '65f53f89b701'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_embeddings",
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type", "entity_id", "chunk_index", "model_id",
            name="uq_ai_embeddings_entity_chunk_model",
        ),
    )
    op.create_index("ix_ai_embeddings_group_id", "ai_embeddings", ["group_id"])
    op.create_index("ix_ai_embeddings_entity", "ai_embeddings", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_embeddings_entity", table_name="ai_embeddings")
    op.drop_index("ix_ai_embeddings_group_id", table_name="ai_embeddings")
    op.drop_table("ai_embeddings")
