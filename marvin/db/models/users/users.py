import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import ConfigDict
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, orm, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, Session, mapped_column

from marvin.core.config import get_app_settings
from marvin.db.models._model_utils.auto_init import auto_init
from marvin.db.models._model_utils.datetime import NaiveDateTime
from marvin.db.models._model_utils.guid import GUID

from .. import BaseMixins, SqlAlchemyBase

if TYPE_CHECKING:
    from ..groups import Groups
    from .password_reset import PasswordResetModel


class LongLiveToken(SqlAlchemyBase, BaseMixins):
    __tablename__ = "long_live_tokens"
    name: Mapped[str] = mapped_column(String, nullable=False)
    token: Mapped[str] = mapped_column(String, nullable=False, index=True)

    user_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("users.id"), index=True)
    user: Mapped[Optional["Users"]] = orm.relationship("Users")

    def __init__(self, name, token, user_id, **_) -> None:
        self.name = name
        self.token = token
        self.user_id = user_id


class AuthMethod(enum.Enum):
    MARVIN = "MARVIN"
    LDAP = "LDAP"
    OIDC = "OIDC"


class Users(SqlAlchemyBase, BaseMixins):
    __tablename__ = "users"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    full_name: Mapped[str | None] = mapped_column(String, index=True)
    username: Mapped[str | None] = mapped_column(String, index=True, unique=True)
    email: Mapped[str | None] = mapped_column(String, unique=True, index=True)
    password: Mapped[str | None] = mapped_column(String)
    auth_method: Mapped[Enum[AuthMethod]] = mapped_column(Enum(AuthMethod), default=AuthMethod.MARVIN)
    admin: Mapped[bool | None] = mapped_column(Boolean, default=False)
    advanced: Mapped[bool | None] = mapped_column(Boolean, default=False)

    group_id: Mapped[GUID] = mapped_column(GUID, ForeignKey("groups.id"), nullable=False, index=True)
    group: Mapped["Groups"] = orm.relationship("Groups", back_populates="users")

    cache_key: Mapped[str | None] = mapped_column(String, default="1234")
    login_attemps: Mapped[int | None] = mapped_column(Integer, default=0)
    locked_at: Mapped[datetime | None] = mapped_column(NaiveDateTime, default=None)

    # Group Permissions
    can_manage: Mapped[bool | None] = mapped_column(Boolean, default=False)
    can_invite: Mapped[bool | None] = mapped_column(Boolean, default=False)

    sp_args = {
        "back_populates": "user",
        "cascade": "all, delete, delete-orphan",
        "single_parent": True,
    }

    tokens: Mapped[list[LongLiveToken]] = orm.relationship(LongLiveToken, **sp_args)
    password_reset_tokens: Mapped[list["PasswordResetModel"]] = orm.relationship("PasswordResetModel", **sp_args)

    model_config = ConfigDict(
        exclude={
            "password",
            "admin",
            "can_manage",
            "can_invite",
            "group",
        }
    )

    @hybrid_property
    def group_slug(self) -> str:
        return self.group.slug

    @auto_init()
    def __init__(self, session: Session, full_name, password, group: str | None = None, **kwargs) -> None:
        if group is None:
            settings = get_app_settings()
            group = group or settings._DEFAULT_GROUP

        from marvin.db.models.groups import Groups

        self.group = session.execute(select(Groups).filter(Groups.name == group)).scalars().one_or_none()

        if self.group is None:
            raise ValueError(f"Group {group} does not exist; cannot create user")

        self.password = password

        if self.username is None:
            self.username = full_name

        self._set_permissions(**kwargs)

    @auto_init()
    def update(self, session: Session, full_name, email, group, username, **kwargs):
        self.username = username
        self.full_name = full_name
        self.email = email

        from marvin.db.models.groups import Groups

        self.group = session.execute(select(Groups).filter(Groups.name == group)).scalars().one_or_none()

        if self.username is None:
            self.username = full_name

        self._set_permissions(**kwargs)

    def update_password(self, password):
        self.password = password

    def _set_permissions(self, admin, can_manage=False, can_invite=False, can_organize=False, **_):
        """Set user permissions based on the admin flag and the passed in kwargs

        Args:
            admin (bool):
            can_manage (bool):
            can_invite (bool):
            can_organize (bool):
        """
        self.admin = admin
        if self.admin:
            self.can_manage = True
            self.can_invite = True
            self.advanced = True
        else:
            self.can_manage = can_manage
            self.can_invite = can_invite
