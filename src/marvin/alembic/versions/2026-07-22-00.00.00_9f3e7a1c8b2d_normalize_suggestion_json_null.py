"""normalize suggestion_json JSON `null` to SQL NULL

The suggestion_json columns (entries/assets/resources) used a plain sa.JSON type, which renders
Python None as the JSON literal `null` rather than SQL NULL. The dashboard "pending AI suggestions"
count filters on `suggestion_json IS NOT NULL`, so every row cleared to None (or defaulted on
insert) was miscounted as a pending suggestion. The model columns now use JSON(none_as_null=True);
this migration cleans up the rows already written as JSON `null`.

Revision ID: 9f3e7a1c8b2d
Revises: c5c7eae2b8bf
Create Date: 2026-07-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9f3e7a1c8b2d'
down_revision: Union[str, None] = 'c5c7eae2b8bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ('entries', 'assets', 'resources')


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        for tbl in _TABLES:
            op.execute(
                f"UPDATE {tbl} SET suggestion_json = NULL "
                f"WHERE suggestion_json IS NOT NULL AND suggestion_json::text = 'null'"
            )
    else:
        # sqlite (and others) store JSON as text; the literal is the 4-char string `null`.
        for tbl in _TABLES:
            op.execute(
                f"UPDATE {tbl} SET suggestion_json = NULL "
                f"WHERE suggestion_json IS NOT NULL AND suggestion_json = 'null'"
            )


def downgrade() -> None:
    # No-op: SQL NULL and JSON `null` are semantically equivalent for this column; the distinction
    # this migration removes was a bug, so there is nothing meaningful to restore.
    pass
