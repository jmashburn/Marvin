from pydantic import UUID4, HttpUrl, ConfigDict
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.db.models.groups import GroupEventNotifierModel, GroupEventNotifierOptionsModel
from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.response.pagination import PaginationBase

# =============================================================================
# Group Events Notifier Options


class GroupEventNotifierOptions(_MarvinModel):
    """
    These events are in-sync with the EventTypes found in the EventBusService.
    If you modify this, make sure to update the EventBusService as well.
    """

    test: bool = True


class GroupEventNotifierOptionsCreate(_MarvinModel):
    namespace: str
    slug: str


class GroupEventNotifierOptionsUpdate(GroupEventNotifierOptionsCreate):
    id: UUID4


class GroupEventNotifierOptionsRead(GroupEventNotifierOptionsCreate):
    model_config = ConfigDict(from_attributes=True)


class GroupEventNotifierOptionsSummary(_MarvinModel):
    option: str
    model_config = ConfigDict(from_attributes=True)


class GroupEventNotifierOptionsPagination(PaginationBase):
    items: list[GroupEventNotifierOptionsSummary]


# =======================================================================
# Notifiers


class GroupEventNotifierCreate(_MarvinModel):
    name: str
    apprise_url: str | None = None
    options: list = []
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "Event Notifier",
                "apprise_url": "json://127.0.0.1:8000",
                "options": ["core.test-message", "core.webhook-task"],
            }
        },
    )


class GroupEventNotifierSave(GroupEventNotifierCreate):
    group_id: UUID4
    options: list = []


class GroupEventNotifierUpdate(GroupEventNotifierSave):
    group_id: UUID4
    enabled: bool = True
    options: list = []


class GroupEventNotifierRead(_MarvinModel):
    id: UUID4
    name: str
    enabled: bool
    group_id: UUID4
    options: list[GroupEventNotifierOptionsSummary] = []
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [joinedload(GroupEventNotifierModel.options)]


class GroupEventNotifierPagination(PaginationBase):
    items: list[GroupEventNotifierRead]


class GroupEventNotifierPrivate(GroupEventNotifierRead):
    apprise_url: str
    model_config = ConfigDict(from_attributes=True)
