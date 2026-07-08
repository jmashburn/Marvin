"""add asset storage fields

Revision ID: e4f9a2b1c3d5
Revises: d8568bbaca53
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4f9a2b1c3d5"
down_revision: Union[str, None] = "d8568bbaca53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add asset storage fields."""
    # Add new columns
    op.add_column("assets", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("filename", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("extension", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("asset_type", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("checksum", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("orientation", sa.Integer(), nullable=True))
    op.add_column("assets", sa.Column("storage_provider", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("storage_key", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("public_url", sa.String(), nullable=True))

    # Backfill existing records with placeholder values
    # Assuming existing assets use local storage
    op.execute("""
        UPDATE assets SET
            original_filename = 'legacy',
            filename = 'legacy',
            extension = '',
            asset_type = 'other',
            checksum = '',
            storage_provider = 'local',
            storage_key = file_path
        WHERE original_filename IS NULL
    """)

    # Make file_path nullable
    op.alter_column("assets", "file_path", nullable=True)

    # Make new columns non-nullable after backfill
    op.alter_column("assets", "original_filename", nullable=False)
    op.alter_column("assets", "filename", nullable=False)
    op.alter_column("assets", "extension", nullable=False)
    op.alter_column("assets", "asset_type", nullable=False)
    op.alter_column("assets", "checksum", nullable=False)
    op.alter_column("assets", "storage_provider", nullable=False)
    op.alter_column("assets", "storage_key", nullable=False)

    # Add unique constraint on storage_key
    op.create_unique_constraint("uq_assets_storage_key", "assets", ["storage_key"])

    # Add index on asset_type
    op.create_index(op.f("ix_assets_asset_type"), "assets", ["asset_type"], unique=False)


def downgrade() -> None:
    """Remove asset storage fields."""
    # Drop constraints and indexes
    op.drop_index(op.f("ix_assets_asset_type"), table_name="assets")
    op.drop_constraint("uq_assets_storage_key", "assets", type_="unique")

    # Make file_path non-nullable again
    op.alter_column("assets", "file_path", nullable=False)

    # Drop new columns
    op.drop_column("assets", "public_url")
    op.drop_column("assets", "storage_key")
    op.drop_column("assets", "storage_provider")
    op.drop_column("assets", "orientation")
    op.drop_column("assets", "checksum")
    op.drop_column("assets", "asset_type")
    op.drop_column("assets", "extension")
    op.drop_column("assets", "filename")
    op.drop_column("assets", "original_filename")
