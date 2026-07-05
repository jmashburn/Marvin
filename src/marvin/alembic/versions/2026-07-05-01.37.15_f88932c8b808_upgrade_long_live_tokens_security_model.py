"""upgrade long_live_tokens security model

BREAKING CHANGE: All existing user API tokens will be revoked.
Users must regenerate tokens after this migration.

This migration upgrades User API Tokens from insecure plaintext JWT storage
to secure bcrypt-hashed tokens matching the API Clients security model.

Security improvements:
- Bcrypt-hashed token storage (no plaintext)
- Token rotation support
- Soft deletion (revoked_at)
- Usage tracking (last_used_at)
- Enable/disable flag
- Audit trail (created_by)

Revision ID: f88932c8b808
Revises: 6caab4aafc42
Create Date: 2026-07-05 01:37:15.392852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = 'f88932c8b808'
down_revision: Union[str, None] = '6caab4aafc42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### User API Tokens Security Upgrade Migration ###
    # BREAKING CHANGE: Revokes all existing user API tokens

    # Step 1: Add new security columns (nullable initially to allow migration)
    with op.batch_alter_table('long_live_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('token_hash', sa.String(), nullable=True))  # Nullable first
        batch_op.add_column(sa.Column('enabled', sa.Boolean(), nullable=True, server_default='true'))
        batch_op.add_column(sa.Column('last_used_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('revoked_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('created_by', marvin.db.migration_types.GUID(), nullable=True))  # Nullable first

    # Step 2: Populate created_by from user_id for existing tokens (audit trail)
    op.execute("""
        UPDATE long_live_tokens
        SET created_by = user_id
        WHERE created_by IS NULL
    """)

    # Step 3: Revoke all existing tokens (BREAKING CHANGE)
    # Mark as revoked and disabled so users must regenerate
    # Use CURRENT_TIMESTAMP for SQLite/PostgreSQL compatibility
    op.execute("""
        UPDATE long_live_tokens
        SET revoked_at = CURRENT_TIMESTAMP,
            enabled = false,
            token_hash = 'MIGRATION_REVOKED'
        WHERE token_hash IS NULL
    """)

    # Step 4: Make columns non-nullable and add constraints
    with op.batch_alter_table('long_live_tokens', schema=None) as batch_op:
        batch_op.alter_column('token_hash', nullable=False)
        batch_op.alter_column('enabled', nullable=False, server_default=None)
        batch_op.alter_column('created_by', nullable=False)
        batch_op.alter_column('user_id', existing_type=sa.CHAR(length=32), nullable=False)

        # Add unique index on token_hash
        batch_op.create_unique_constraint('uq_long_live_tokens_token_hash', ['token_hash'])

    # Step 5: Drop the old plaintext token column and its index
    with op.batch_alter_table('long_live_tokens', schema=None) as batch_op:
        batch_op.drop_column('token')  # This will also drop the index


def downgrade() -> None:
    # Rollback: Restore old schema (WARNING: loses all new token data)
    # Re-add the old plaintext token column
    with op.batch_alter_table('long_live_tokens', schema=None) as batch_op:
        batch_op.add_column(sa.Column('token', sa.String(), nullable=True))
        batch_op.create_index('ix_long_live_tokens_token', ['token'], unique=True)

    # Drop new security columns and constraints
    with op.batch_alter_table('long_live_tokens', schema=None) as batch_op:
        batch_op.drop_constraint('uq_long_live_tokens_token_hash', type_='unique')
        batch_op.alter_column('user_id', existing_type=sa.CHAR(length=32), nullable=True)
        batch_op.drop_column('created_by')
        batch_op.drop_column('revoked_at')
        batch_op.drop_column('last_used_at')
        batch_op.drop_column('enabled')
        batch_op.drop_column('token_hash')
        batch_op.drop_column('description')
