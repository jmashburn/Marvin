"""add_workspace_site_settings

Revision ID: 4b869d573a78
Revises: ba8612ae5c08
Create Date: 2026-07-05 12:24:53.717648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = '4b869d573a78'
down_revision: Union[str, None] = 'ba8612ae5c08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add site configuration columns to group_preferences table
    # These allow each workspace to define its public site identity

    # Core site identity
    op.add_column('group_preferences', sa.Column('site_title', sa.String(), nullable=True))
    op.add_column('group_preferences', sa.Column('site_tagline', sa.String(), nullable=True))
    op.add_column('group_preferences', sa.Column('site_description', sa.String(), nullable=True))

    # URLs and assets
    op.add_column('group_preferences', sa.Column('site_canonical_url', sa.String(), nullable=True))
    op.add_column('group_preferences', sa.Column('site_logo', sa.String(), nullable=True))
    op.add_column('group_preferences', sa.Column('site_favicon', sa.String(), nullable=True))

    # Localization
    op.add_column('group_preferences', sa.Column('site_locale', sa.String(), nullable=True, server_default='en-US'))
    op.add_column('group_preferences', sa.Column('site_timezone', sa.String(), nullable=True, server_default='America/New_York'))

    # Contact and social
    op.add_column('group_preferences', sa.Column('site_contact_email', sa.String(), nullable=True))
    op.add_column('group_preferences', sa.Column('site_social_json', sa.JSON(), nullable=True))

    # Flexible metadata for framework-specific or future settings
    op.add_column('group_preferences', sa.Column('site_metadata_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove site configuration columns
    op.drop_column('group_preferences', 'site_metadata_json')
    op.drop_column('group_preferences', 'site_social_json')
    op.drop_column('group_preferences', 'site_contact_email')
    op.drop_column('group_preferences', 'site_timezone')
    op.drop_column('group_preferences', 'site_locale')
    op.drop_column('group_preferences', 'site_favicon')
    op.drop_column('group_preferences', 'site_logo')
    op.drop_column('group_preferences', 'site_canonical_url')
    op.drop_column('group_preferences', 'site_description')
    op.drop_column('group_preferences', 'site_tagline')
    op.drop_column('group_preferences', 'site_title')
