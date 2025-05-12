"""Initialize Tables

Revision ID: 096bd305c0d2
Revises:
Create Date: 2025-05-11 21:28:01.976712

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import marvin.db.migration_types

# revision identifiers, used by Alembic.
revision: str = "096bd305c0d2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_groups_name"), "groups", ["name"], unique=True)
    op.create_table(
        "group_preferences",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("private_group", sa.Boolean(), nullable=True),
        sa.Column("first_day_of_week", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "group_events_notifiers",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("apprise_url", sa.String(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_group_events_notifiers_group_id"), "group_events_notifiers", ["group_id"], unique=False)
    op.create_table(
        "server_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("completed_date", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("log", sa.String(), nullable=True),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_server_tasks_group_id"), "server_tasks", ["group_id"], unique=False)
    op.create_table(
        "webhook_urls",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("time", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_urls_group_id"), "webhook_urls", ["group_id"], unique=False)
    op.create_table(
        "group_events_notifier_options",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("event_notifier_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_notifier_id"],
            ["group_events_notifiers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password", sa.String(), nullable=True),
        sa.Column("admin", sa.Boolean(), nullable=True),
        sa.Column("advanced", sa.Boolean(), nullable=True),
        sa.Column("group_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("cache_key", sa.String(), nullable=True),
        sa.Column("can_manage", sa.Boolean(), nullable=True),
        sa.Column("can_invite", sa.Boolean(), nullable=True),
        sa.Column("can_organize", sa.Boolean(), nullable=True),
        sa.Column("owned_recipes_id", marvin.db.migration_types.GUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["groups.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_full_name"), "users", ["full_name"], unique=False)
    op.create_index(op.f("ix_users_group_id"), "users", ["group_id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_table(
        "long_live_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("user_id", marvin.db.migration_types.GUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("update_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", marvin.db.migration_types.GUID(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )


def downgrade() -> None:
    pass
