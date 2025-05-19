from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, TypeVar

from pydantic import UUID4, BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.core.config import get_app_settings
from marvin.db.models.users import Users
from marvin.db.models.users.users import AuthMethod, LongLiveToken
from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.response.pagination import PaginationBase

DataT = TypeVar("DataT", bound=BaseModel)
DEFAULT_INTEGRATION_ID = "generic"
settings = get_app_settings()


class LongLiveTokenCreate(_MarvinModel):
    id: UUID4 | None = None
    name: str
    integration_id: str = DEFAULT_INTEGRATION_ID


class LongLiveTokenRead(_MarvinModel):
    id: UUID4
    name: str
    created_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [joinedload(LongLiveToken.user)]


class LongLiveTokenCreateResponse(_MarvinModel):
    """Should ONLY be used when creating a new token, as the token field is sensitive"""

    token: str


class TokenCreate(LongLiveTokenCreate):
    user_id: UUID4
    token: str
    model_config = ConfigDict(from_attributes=True)


class TokenResponseDelete(_MarvinModel):
    token_delete: str
    model_config = ConfigDict(from_attributes=True)


class ChangePassword(_MarvinModel):
    current_password: str = ""
    new_password: str = Field(..., min_length=8)


class UserCreate(_MarvinModel):
    id: UUID4 | None = None
    username: str | None = None
    full_name: str | None = None
    email: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)]
    auth_method: AuthMethod = AuthMethod.MARVIN
    admin: bool = False
    group: str | None = None
    advanced: bool = False
    password: str
    can_invite: bool = False
    can_manage: bool = False
    can_organize: bool = False
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "username": "ChangeMe",
                "fullName": "Change Me",
                "email": "changeme@example.com",
                "group": settings._DEFAULT_GROUP,
                "admin": "false",
            }
        },
    )

    @field_validator("group", mode="before")
    def convert_group_to_name(cls, v):
        if not v or isinstance(v, str):
            return v

        try:
            return v.name
        except AttributeError:
            return v


class UserSave(UserCreate):
    username: str
    full_name: str
    password: str


class UserRead(UserCreate):
    id: UUID4
    group: str
    group_id: UUID4
    group_slug: str
    # tokens: list[LongLiveTokenRead] | None = None
    cache_key: str
    model_config = ConfigDict(from_attributes=True)

    @property
    def is_default_user(self) -> bool:
        return self.email == settings._DEFAULT_EMAIL.strip().lower()

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [joinedload(Users.group), joinedload(Users.tokens)]


class UserSummary(_MarvinModel):
    id: UUID4
    group_id: UUID4
    username: str
    full_name: str
    model_config = ConfigDict(from_attributes=True)


class UserPagination(PaginationBase):
    items: list[UserRead]


class UserSummaryPagination(PaginationBase):
    items: list[UserSummary]


class PrivateUser(UserRead):
    password: str
    login_attemps: int = 0
    locked_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)

    @field_validator("login_attemps", mode="before")
    @classmethod
    def none_to_zero(cls, v):
        return 0 if v is None else v

    @property
    def is_locked(self) -> bool:
        if self.locked_at is None:
            return False

        lockout_expires_at = self.locked_at + timedelta(hours=get_app_settings().SECURITY_USER_LOCKOUT_TIME)
        return lockout_expires_at > datetime.now(timezone.utc)

    def directory(self) -> Path:
        return PrivateUser.get_directory(self.id)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [joinedload(Users.group), joinedload(Users.tokens)]


class LongLiveTokenRead_(TokenCreate):
    id: UUID4
    user: PrivateUser
    model_config = ConfigDict(from_attributes=True)
