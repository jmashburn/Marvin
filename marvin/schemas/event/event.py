from pydantic import UUID4, HttpUrl, ConfigDict
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.db.models.events import EventNotifierOptionsModel
from marvin.schemas._marvin import _MarvinModel
from marvin.schemas.response.pagination import PaginationBase

# =============================================================================
# Events Notifier Options


class EventNotifierOptions(_MarvinModel):
    """
    These events are in-sync with the EventTypes found in the EventBusService.
    If you modify this, make sure to update the EventBusService as well.
    """

    test: bool = True


class EventNotifierOptionsCreate(_MarvinModel):
    name: str
    namespace: str
    description: str | None = None
    enabled: bool | None = False


class EventNotifierOptionsUpdate(EventNotifierOptionsCreate):
    id: UUID4


class EventNotifierOptionsRead(_MarvinModel):
    name: str
    description: str
    enabled: bool | None = False
    model_config = ConfigDict(from_attributes=True)


class EventNotifierOptionsSummary(EventNotifierOptionsRead):
    option: str
    model_config = ConfigDict(from_attributes=True)


class EventNotifierOptionsPagination(PaginationBase):
    items: list[EventNotifierOptionsSummary]
