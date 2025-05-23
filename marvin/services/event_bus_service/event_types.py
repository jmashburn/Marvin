import uuid
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any

from pydantic import UUID4, SerializeAsAny, field_validator

from marvin.schemas._marvin import _MarvinModel

INTERNAL_INTEGRATION_ID = "marvin_generic_user"


class EventNameSpaceBase(Enum): ...


class EventNameSpace(EventNameSpaceBase):
    namespace = "core"


class EventTypeBase(Enum): ...


class EventTypes(EventTypeBase):
    """
    The event type defines whether or not a subscriber should receive an event.

    Each event type is represented by a field on the subscriber repository, therefore any changes
    made here must also be reflected in the database (and likely requires a database migration).

    If you'd like more granular control over the metadata of the event, e.g. events for sub-records
    (like shopping list items), modify the event document type instead (which is not tied to a database entry).
    """

    # used internally and cannot be subscribed to
    test_message = auto()
    webhook_task = auto()
    user_signup = auto()


class EventDocumentTypeBase(Enum): ...


class EventDocumentType(EventDocumentTypeBase):
    generic = "generic"
    user = "user"


class EventOperationBase(Enum): ...


class EventOperation(EventOperationBase):
    info = "info"
    create = "create"
    update = "update"
    delete = "delete"


class EventDocumentDataBase(_MarvinModel):
    document_type: EventDocumentTypeBase | None = None
    operation: EventOperationBase
    ...


class EventTokenRefreshData(EventDocumentDataBase):
    document_type: EventDocumentTypeBase = EventDocumentType.generic
    operation: EventOperationBase = EventOperation.info
    username: str
    token: str


class EventUserSignupData(EventDocumentDataBase):
    document_type: EventDocumentTypeBase = EventDocumentType.user
    operation: EventOperationBase = EventOperation.create
    username: str
    email: str


class EventWebhookData(EventDocumentDataBase):
    webhook_start_dt: datetime
    webhook_end_dt: datetime
    webhook_body: Any = None


class EventBusMessage(_MarvinModel):
    title: str
    body: str = ""

    @classmethod
    def from_type(cls, event_type: EventTypes, body: str = "") -> "EventBusMessage":
        # title = event_type.name.replace("_", " ").title()
        title = event_type.name.replace("_", " ").title()
        return cls(title=title, body=body)

    @field_validator("body")
    def populate_body(v):
        # if the body is empty, apprise won't send the notification
        return v or "generic"


class Event(_MarvinModel):
    message: EventBusMessage
    event_type: EventTypeBase
    integration_id: str
    document_data: SerializeAsAny[EventDocumentDataBase]

    # set at instantiation
    event_id: UUID4 | None = None
    timestamp: datetime | None = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.event_id = uuid.uuid4()
        self.timestamp = datetime.now(timezone.utc)
