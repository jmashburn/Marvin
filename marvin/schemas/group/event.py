from pydantic import UUID4, HttpUrl, ConfigDict
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.db.models.groups import GroupEventNotifierModel
from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.response.pagination import PaginationBase

# =============================================================================
# Group Events Notifier Options


class GroupEventNotifierOptions(_MarvinModel):
    """
    These events are in-sync with the EventTypes found in the EventBusService.
    If you modify this, make sure to update the EventBusService as well.
    """

    test_message: bool = False
    webhook_task: bool = False
    user_signup: bool = False
    data_export: bool = True


class GroupEventNotifierOptionsUpdate(GroupEventNotifierOptions):
    notifier_id: UUID4


class GroupEventNotifierOptionsRead(GroupEventNotifierOptions):
    id: UUID4
    model_config = ConfigDict(from_attributes=True)


# =======================================================================
# Notifiers


class GroupEventNotifierCreate(_MarvinModel):
    name: str
    apprise_url: str | None = None


class GroupEventNotifierSave(GroupEventNotifierCreate):
    enabled: bool = True
    group_id: UUID4
    options: GroupEventNotifierOptions = GroupEventNotifierOptions()


class GroupEventNotifierUpdate(GroupEventNotifierSave):
    id: UUID4
    apprise_url: HttpUrl | None = None


class GroupEventNotifierRead(_MarvinModel):
    id: UUID4
    name: str
    enabled: bool
    group_id: UUID4
    options: GroupEventNotifierOptionsRead
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [joinedload(GroupEventNotifierModel.options)]


class GroupEventNotifierPagination(PaginationBase):
    items: list[GroupEventNotifierRead]


class GroupEventNotifierPrivate(GroupEventNotifierRead):
    apprise_url: str
    model_config = ConfigDict(from_attributes=True)
