from typing import Annotated

from pydantic import UUID4, ConfigDict, StringConstraints
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.db.models.groups import Groups
from marvin.db.models.users import Users
from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.response.pagination import PaginationBase

from ..user import UserSummary
from .preferences import GroupPreferencesRead, GroupPreferencesUpdate
from .webhook import WebhookCreate, WebhookRead


class GroupCreate(_MarvinModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    model_config = ConfigDict(from_attributes=True)


class GroupAdminUpdate(GroupCreate):
    id: UUID4
    name: str
    preferences: GroupPreferencesUpdate | None = None


class GroupUpdate(GroupCreate):
    id: UUID4
    name: str
    webhooks: list[WebhookCreate] = []


class GroupRead(GroupUpdate):
    id: UUID4
    users: list[UserSummary] | None = None
    preferences: GroupPreferencesRead | None = None
    webhooks: list[WebhookRead] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [
            joinedload(Groups.webhooks),
            joinedload(Groups.preferences),
            selectinload(Groups.users).joinedload(Users.group),
            selectinload(Groups.users).joinedload(Users.tokens),
        ]


class GroupSummary(GroupCreate):
    id: UUID4
    name: str
    slug: str
    preferences: GroupPreferencesRead | None = None

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [
            joinedload(Groups.preferences),
        ]


class GroupPagination(PaginationBase):
    items: list[GroupRead]
