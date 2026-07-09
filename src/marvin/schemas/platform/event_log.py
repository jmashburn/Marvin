"""Event log schemas."""

from datetime import datetime

from pydantic import ConfigDict, UUID4

from marvin.schemas._marvin import _MarvinModel


class EventLogRead(_MarvinModel):
    """Schema for reading an event log entry."""

    id: UUID4
    event_id: UUID4
    event_type: str
    occurred_at: datetime
    workspace_id: UUID4
    user_id: UUID4 | None = None
    entity_id: UUID4 | None = None
    entity_type: str | None = None
    integration_id: str
    operation: str | None = None
    event_data: dict
    message_title: str
    message_body: str | None = None
    created_at: datetime | None = None
    update_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EventLogSummary(_MarvinModel):
    """Summary schema for an event log entry (lighter payload)."""

    id: UUID4
    event_id: UUID4
    event_type: str
    occurred_at: datetime
    workspace_id: UUID4
    user_id: UUID4 | None = None
    entity_id: UUID4 | None = None
    entity_type: str | None = None
    message_title: str
    message_body: str | None = None

    model_config = ConfigDict(from_attributes=True)
