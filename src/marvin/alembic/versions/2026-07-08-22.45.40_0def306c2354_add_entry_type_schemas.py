"""add_entry_type_schemas

This migration transforms Entry Types from simple categorizations into schema-driven
content models. It:

1. Adds schema_json to entry_types table (JSONB)
2. Adds data_json to entries table (JSONB)
3. Migrates existing content_markdown to data_json.body
4. Drops content_markdown column

This is a BREAKING CHANGE that requires coordinated backend + SDK updates.

Revision ID: 0def306c2354
Revises: d1d2bc0fed86
Create Date: 2026-07-08 22:45:40.131633

"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = "0def306c2354"
down_revision: Union[str, None] = "d1d2bc0fed86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default schema for existing entry types (single markdown field)
DEFAULT_SCHEMA = {"fields": [{"key": "body", "label": "Content", "type": "markdown", "required": False}]}


def upgrade() -> None:
    """
    Upgrade to schema-driven entry types.

    Migration strategy:
    1. Add new columns (schema_json, data_json)
    2. Populate with default values
    3. Migrate content_markdown -> data_json.body
    4. Drop content_markdown column
    """
    connection = op.get_bind()

    # Step 1: Add schema_json to entry_types (nullable initially)
    op.add_column("entry_types", sa.Column("schema_json", JSONB(), nullable=True))

    # Step 2: Add data_json to entries (nullable initially)
    op.add_column("entries", sa.Column("data_json", JSONB(), nullable=True))

    # Step 3: Populate default schema for all entry types
    connection.execute(
        sa.text("""
            UPDATE entry_types
            SET schema_json = :schema
            WHERE schema_json IS NULL
        """),
        {"schema": json.dumps(DEFAULT_SCHEMA)},
    )

    # Step 4: Migrate content_markdown to data_json.body
    # For entries with content_markdown, create {body: content_markdown}
    connection.execute(
        sa.text("""
            UPDATE entries
            SET data_json = jsonb_build_object('body', content_markdown)
            WHERE content_markdown IS NOT NULL
        """)
    )

    # Step 5: Set empty object for entries with no content
    connection.execute(
        sa.text("""
            UPDATE entries
            SET data_json = '{}'::jsonb
            WHERE data_json IS NULL
        """)
    )

    # Step 6: Make columns NOT NULL now that they're populated
    op.alter_column("entry_types", "schema_json", nullable=False, server_default="{}")

    op.alter_column("entries", "data_json", nullable=False, server_default="{}")

    # Step 7: Drop old content_markdown column
    op.drop_column("entries", "content_markdown")


def downgrade() -> None:
    """
    Downgrade from schema-driven entry types back to simple markdown.

    WARNING: This will lose data for entries using non-body fields!
    Only the 'body' field is extracted back to content_markdown.
    """
    connection = op.get_bind()

    # Step 1: Add content_markdown column back
    op.add_column("entries", sa.Column("content_markdown", sa.Text(), nullable=True))

    # Step 2: Extract data_json.body -> content_markdown
    connection.execute(
        sa.text("""
            UPDATE entries
            SET content_markdown = data_json->>'body'
            WHERE data_json ? 'body'
        """)
    )

    # Step 3: Drop new columns
    op.drop_column("entries", "data_json")
    op.drop_column("entry_types", "schema_json")
