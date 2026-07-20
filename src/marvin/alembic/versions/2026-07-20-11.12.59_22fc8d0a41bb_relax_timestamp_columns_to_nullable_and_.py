"""relax timestamp columns to nullable and drop NOW server defaults

Five tables were created by the hand-written initial schema with
`created_at`/`update_at` as NOT NULL, four of them also carrying
`server_default=sa.text("NOW()")`. Both diverge from `SqlAlchemyBase`, which
declares these columns as `Mapped[datetime | None]` with a Python-side
`default=get_utc_now` / `onupdate=get_utc_now`.

`NOW()` is Postgres syntax. SQLite stores it verbatim and has no such function, so
an insert omitting `created_at` fails with `unknown function: NOW()`. It has never
fired only because the application always supplies a value. Rather than swap it for
`sa.func.now()`, the server defaults are dropped outright: the backend owns these
timestamps, which keeps the schema portable instead of tied to one database.

Net effect: the database now matches the models — nullable, no server default.

NOTE: `forms`, `form_submissions` and `form_rate_limits` are covered here by hand.
`alembic/env.py` imports only `SqlAlchemyBase`, never the model modules, and
`include_object` skips any table missing from the metadata — so those three are
invisible to `--autogenerate`, which emitted nothing for them.

Revision ID: 22fc8d0a41bb
Revises: f0382e299d4e
Create Date: 2026-07-20 11:12:59.350599

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '22fc8d0a41bb'
down_revision: Union[str, None] = 'f0382e299d4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every table whose timestamps were created NOT NULL.
TABLES = ("event_log", "scheduled_tasks", "forms", "form_submissions", "form_rate_limits")
# Of those, the ones that also carried a NOW() server default (event_log did not).
TABLES_WITH_DEFAULT = ("scheduled_tasks", "forms", "form_submissions", "form_rate_limits")
COLUMNS = ("created_at", "update_at")


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in COLUMNS:
                batch_op.alter_column(
                    column,
                    existing_type=sa.DateTime(),
                    nullable=True,
                    server_default=None,  # drop it — the application sets these
                )


def downgrade() -> None:
    # Faithful inverse: restore NOT NULL everywhere, and the NOW() default only where it
    # existed. Note this reinstates a default SQLite cannot evaluate.
    for table in TABLES:
        with op.batch_alter_table(table, schema=None) as batch_op:
            for column in COLUMNS:
                batch_op.alter_column(
                    column,
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("NOW()") if table in TABLES_WITH_DEFAULT else None,
                )
