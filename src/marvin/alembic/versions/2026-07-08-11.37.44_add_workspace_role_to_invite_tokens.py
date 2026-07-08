"""add workspace_role to invite_tokens

Revision ID: b5c6d7e8f9a0
Revises: a3f8e9c4d2b1
Create Date: 2026-07-08 11:37:44

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b5c6d7e8f9a0"
down_revision = "a3f8e9c4d2b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add workspace_role column to invite_tokens table."""
    # Add workspace_role column with default value of 'EDITOR'
    # Using VARCHAR/TEXT with CHECK constraint for the enum
    op.add_column(
        "invite_tokens",
        sa.Column(
            "workspace_role",
            sa.String(),
            nullable=False,
            server_default="EDITOR",
            doc="The role that invited users will receive when they join this workspace.",
        ),
    )

    # Add check constraint to ensure valid role values
    op.create_check_constraint(
        "ck_invite_tokens_workspace_role", "invite_tokens", "workspace_role IN ('OWNER', 'ADMIN', 'EDITOR', 'AUTHOR', 'VIEWER')"
    )


def downgrade() -> None:
    """Remove workspace_role column from invite_tokens table."""
    # Drop the check constraint first
    op.drop_constraint("ck_invite_tokens_workspace_role", "invite_tokens", type_="check")

    # Drop the column
    op.drop_column("invite_tokens", "workspace_role")
