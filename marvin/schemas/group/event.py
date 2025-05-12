from pydantic import UUID4, ConfigDict
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.db.models.groups import GroupEventNotifierModel
from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.response.pagination import PaginationBase

# =============================================================================
# Group Events Notifier Options


class GroupEventNotifierOptionsModel(_MarvinModel): ...


class GroupEventNotifierOptionsCreate(GroupEventNotifierOptionsModel):
    """
    These events are in-sync with the EventTypes found in the EventBusService.
    If you modify this, make sure to update the EventBusService as well.
    """

    test_message: bool = False
    webhook_task: bool = False


class GroupEventNotifierOptionsUpdate(GroupEventNotifierOptionsModel):
    notifier_id: UUID4


class GroupEventNotifierOptionsRead(GroupEventNotifierOptionsModel):
    id: UUID4
    model_config = ConfigDict(from_attributes=True)


# =======================================================================
# Notifiers


class GroupEventNotifierModel(_MarvinModel): ...


class GroupEventNotifierCreate(GroupEventNotifierModel):
    name: str
    apprise_url: str | None = None


class GroupEventNotifierUpdate(GroupEventNotifierCreate):
    enabled: bool = True
    group_id: UUID4
    apprise_url: str | None = None
    options: GroupEventNotifierOptionsCreate = GroupEventNotifierOptionsCreate()


class GroupEventNotifierRead(_MarvinModel):
    id: UUID4
    name: str
    enabled: bool
    group_id: UUID4
    options: GroupEventNotifierOptionsRead
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [joinedload(GroupEventNotifierUpdate.options)]


class GroupEventNotifierPagination(PaginationBase):
    items: list[GroupEventNotifierRead]


class GroupEventNotifierPrivate(GroupEventNotifierRead):
    apprise_url: str
    model_config = ConfigDict(from_attributes=True)
