"""add rendering and capabilities to entry_types

Revision ID: dfcf359a332b
Revises: d1d2bc0fed86
Create Date: 2026-07-12 13:47:45.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "dfcf359a332b"
down_revision: Union[str, None] = "d1d2bc0fed86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("entry_types", sa.Column("rendering_json", sa.JSON(), nullable=True))
    op.add_column("entry_types", sa.Column("capabilities_json", sa.JSON(), nullable=True))
    op.add_column("entry_types", sa.Column("is_rendered", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    entry_types = sa.table(
        "entry_types",
        sa.column("slug", sa.String),
        sa.column("is_system", sa.Boolean),
        sa.column("is_rendered", sa.Boolean),
        sa.column("rendering_json", sa.JSON),
    )
    CORE_RENDERER_TYPES = {
        "page": {"renderer": "page", "package": "@inneropen/marvin-renderers-core"},
        "article": {"renderer": "article", "package": "@inneropen/marvin-renderers-core"},
        "faq": {"renderer": "faq", "package": "@inneropen/marvin-renderers-core"},
        "navigation-item": {"renderer": "navigation", "package": "@inneropen/marvin-renderers-core"},
    }
    for slug, rendering in CORE_RENDERER_TYPES.items():
        op.execute(
            entry_types.update()
            .where(entry_types.c.slug == slug)
            .where(entry_types.c.is_system.is_(True))
            .values(is_rendered=True, rendering_json=rendering)
        )


def downgrade() -> None:
    op.drop_column("entry_types", "is_rendered")
    op.drop_column("entry_types", "capabilities_json")
    op.drop_column("entry_types", "rendering_json")
