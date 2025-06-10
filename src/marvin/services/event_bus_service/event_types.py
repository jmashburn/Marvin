"""
This module defines the core enumerations and Pydantic models that structure
events within the Marvin application's event bus system.

These types are used to create, categorize, and carry data for events that
are dispatched and handled by various listeners and publishers.
"""

import uuid  # For generating unique event IDs
from datetime import UTC, datetime  # For timestamping events
from enum import Enum, auto  # For creating enumerations
from typing import Any  # For generic type hints

from pydantic import (
    UUID4,
    Field,
    SerializeAsAny,
    field_validator,
)  # Core Pydantic components. Removed unused ValidationInfo.

from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model

# Default integration ID for events originating from generic user actions or internal Marvin processes.
INTERNAL_INTEGRATION_ID = "marvin_generic_user"


class EventNameSpaceBase(Enum):
    """
    Abstract base class for event namespaces.
    Subclasses should define actual namespace values.
    """

    ...  # Ellipsis indicates this is an abstract base intended for subclassing.


class EventNameSpace(EventNameSpaceBase):
    """
    Enumeration defining namespaces for categorizing events.
    Namespaces help in organizing and filtering events.
    """

    namespace = "core"
    """The 'core' namespace, likely for fundamental application events."""
    # Example: USER = "user_events", TASK = "task_events"


class EventTypeBase(Enum):
    """
    Abstract base class for event types.
    Subclasses should define specific event types using `auto()` or string values.
    """

    ...  # Ellipsis indicates this is an abstract base.


class EventTypes(EventTypeBase):
    """
    Enumeration of specific event types within the application.

    The event type is crucial for determining which subscribers (listeners)
    should receive and process an event. Each event type defined here typically
    corresponds to a configurable notification option or an internal trigger.

    If these event types are stored in a database (e.g., for user subscriptions),
    changes here (additions, renames, deletions) might require corresponding
    database migrations to keep them in sync.

    For more granular metadata about the event (e.g., specific details of a
    sub-record involved in an event, like a shopping list item), the
    `EventDocumentDataBase` and its subclasses should be used, as they are not
    directly tied to database subscription fields like these event types might be.
    """

    # Internal event types, often not directly subscribable by end-users but used by system components.
    test_message = auto()
    """A test message event, used for verifying notifier configurations."""
    webhook_task = auto()
    """An event that triggers scheduled webhook processing."""
    user_signup = auto()
    """Event dispatched when a new user signs up."""
    user_authenticated = auto()
    """Event dispatched when a user authenticates."""

    # Application-specific events (examples):
    # RECIPE_CREATED = "recipe_created"
    # RECIPE_UPDATED = "recipe_updated"
    # SHOPPING_LIST_GENERATED = "shopping_list_generated"
    token_refreshed = auto()  # Added from auth_controller example
    """Event dispatched when a user's access token is refreshed."""


class EventDocumentTypeBase(Enum):
    """
    Abstract base class for event document types.
    Defines the category of the data/document associated with an event.
    """

    ...


class EventDocumentType(EventDocumentTypeBase):
    """
    Enumeration for the type of document or data payload associated with an event.
    Helps listeners understand the nature of `EventDocumentDataBase` content.
    """

    generic = "generic"
    """A generic document type, for events with non-specific or simple data."""
    user = "user"
    """Indicates the event data pertains to a user entity."""
    # Example: RECIPE = "recipe", SHOPPING_LIST = "shopping_list"


class EventOperationBase(Enum):
    """
    Abstract base class for event operation types.
    Describes the action performed that led to the event (e.g., create, update).
    """

    ...


class EventOperation(EventOperationBase):
    """
    Enumeration for the type of operation that an event represents.
    Commonly used for CRUD-like events or informational messages.
    """

    info = "info"  # Informational event, not necessarily a data change.
    create = "create"  # Event related to the creation of a resource.
    update = "update"  # Event related to the update of a resource.
    delete = "delete"  # Event related to the deletion of a resource.


class EventDocumentDataBase(_MarvinModel):
    """
    Base Pydantic model for the data payload (document) of an event.
    Subclasses should define specific fields relevant to their document type and operation.

    NOTE: This model currently uses `...` (Ellipsis) as a placeholder for fields.
    It should ideally have common fields or be fully abstract if no common fields exist
    beyond `document_type` and `operation` which are often set by subclasses.
    """

    document_type: EventDocumentTypeBase | None = None
    """The type of document/data this payload represents (e.g., generic, user)."""
    operation: EventOperationBase  # Should this be optional or have a default?
    """The operation that this event pertains to (e.g., create, info)."""
    # Ellipsis (`...`) as a field definition is unusual in Pydantic.
    # It implies the field is required but its type is not specified here,
    # or it's a placeholder for subclasses to define actual data fields.
    # If this is intended as a base with no common data fields beyond type/op,
    # it can be left as is, or fields can be made `Any` if truly variable.
    # For now, assuming subclasses will define their specific data fields.
    # If `...` means "no other fields", it can be removed.
    # If it's a placeholder for actual fields, they should be defined.
    # For a base class, it's common to have no fields or only truly common ones.
    # Removing `...` as it's not standard Pydantic field definition.
    # Subclasses will add their own specific fields.


class EventTokenRefreshData(EventDocumentDataBase):
    """
    Data payload for an event indicating a user's access token has been refreshed.
    """

    document_type: EventDocumentTypeBase = EventDocumentType.generic  # Specific document type
    operation: EventOperationBase = EventOperation.info  # Operation type is informational
    username: str
    """The username of the user whose token was refreshed."""
    token: str  # This is the new token. Consider if sending tokens via event bus is secure.
    """The new access token. Sensitive: ensure event bus and listeners handle this securely."""


class EventUserSignupData(EventDocumentDataBase):
    """
    Data payload for an event indicating a new user has signed up.
    """

    document_type: EventDocumentTypeBase = EventDocumentType.user  # Specific document type
    operation: EventOperationBase = EventOperation.create  # Operation type is creation
    username: str
    """The username of the newly signed-up user."""
    email: str
    """The email address of the newly signed-up user."""


class EventWebhookData(EventDocumentDataBase):
    """
    Data payload specifically for `webhook_task` events.
    Contains information needed by WebhookEventListener to find and trigger scheduled webhooks.
    """

    webhook_start_dt: datetime
    """The start datetime for the window in which to find scheduled webhooks."""
    webhook_end_dt: datetime
    """The end datetime for the window in which to find scheduled webhooks."""
    webhook_body: Any = None  # Body to be sent by the webhook, can be dynamically generated.
    """
    The body/payload to be sent by the webhook. This can be populated dynamically
    by the `WebhookEventListener` based on `webhook_type`. Defaults to None.
    """
    # document_type and operation would be set by the dispatcher of webhook_task events.
    # e.g., document_type = EventDocumentType.generic, operation = EventOperation.info


class EventBusMessage(_MarvinModel):
    """
    Pydantic model for the user-facing message content within an event.
    Includes a title and a body for the notification.
    """

    title: str
    """The title of the event message (e.g., for a notification header)."""
    body: str = ""
    """The main body content of the event message. Defaults to an empty string."""

    @classmethod
    def from_type(cls, event_type: EventTypes, body: str = "") -> "EventBusMessage":
        """
        Factory method to create an `EventBusMessage` from an `EventTypes` enum member.
        The title is automatically generated by formatting the enum member's name
        (replacing underscores with spaces and title-casing).

        Args:
            event_type (EventTypes): The enum member representing the type of event.
            body (str, optional): The body content for the message. Defaults to "".

        Returns:
            EventBusMessage: A new instance of `EventBusMessage`.
        """
        # Generate a title from the event type's name (e.g., user_signup -> "User Signup")
        generated_title = event_type.name.replace("_", " ").title()
        return cls(title=generated_title, body=body)

    @field_validator("body", mode="before")  # Run before Pydantic's own validation
    @classmethod
    def ensure_body_is_not_empty_for_apprise(cls, v: str | None) -> str:  # Renamed, added cls, type hint for v
        """
        Pydantic validator to ensure the 'body' field is not empty.

        If the body is empty or None, it defaults to the string "generic".
        This is to prevent issues with services like Apprise that might not
        send notifications if the body is empty.

        Args:
            v (str | None): The input value for the 'body' field.

        Returns:
            str: The validated (and potentially defaulted) body string.
        """
        # If the body is empty or None, Apprise might not send the notification.
        # Default to "generic" to ensure something is sent.
        return v if v and v.strip() else "generic"  # Ensure non-empty and not just whitespace


class Event(_MarvinModel):
    """
    The main Pydantic model representing an event to be dispatched via the event bus.

    Encapsulates the message content, event type, source integration ID,
    and any associated document data. Event ID and timestamp are automatically
    generated upon instantiation.
    """

    message: EventBusMessage
    """The user-facing message content of the event."""
    event_type: EventTypeBase  # Should be EventTypes for specific values
    """The type of the event (e.g., user_signup, test_message)."""
    integration_id: str
    """An identifier for the system or integration that generated the event."""

    # `SerializeAsAny` allows `document_data` to be any subclass of `EventDocumentDataBase`
    # and be correctly serialized/deserialized by Pydantic if `type` field is used for discrimination.
    document_data: SerializeAsAny[EventDocumentDataBase] | None  # Made optional
    """
    The data payload associated with the event. Its specific schema depends on
    the `event_type` and `document_data.document_type`. Can be None.
    """

    # Fields automatically set at instantiation
    event_id: UUID4 = Field(default_factory=uuid.uuid4)
    """A unique identifier for this specific event instance."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """Timestamp (UTC) of when the event object was created."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initializes an Event instance.

        Event ID and timestamp are automatically generated if not provided.
        The `super().__init__` handles Pydantic model initialization with `kwargs`.
        `*args` is included for flexibility but typically not used with Pydantic.
        """
        # Pydantic v2 handles default_factory for event_id and timestamp automatically.
        # Explicit setting in __init__ is more of a Pydantic v1 pattern or for complex defaults.
        # If `event_id` and `timestamp` are meant to be overridable via kwargs but default
        # if not given, Field(default_factory=...) is the idiomatic Pydantic v2 way.
        # The original code had them as `None` initially then set in `__init__`.
        # With `default_factory` in field definitions, this explicit __init__ for them is not strictly needed
        # unless there's logic before `super().__init__` that they depend on, which isn't the case here.
        super().__init__(*args, **kwargs)
        # If event_id or timestamp were passed in kwargs, super().__init__ would have set them.
        # If not, default_factory would be used.
        # This re-assignment ensures they are always set, overriding any potential None from kwargs
        # if the fields were not Optional[None] = Field(default=None) but just Optional[None].
        # Given default_factory, this is fine but slightly redundant unless kwargs might pass `None`.
        if self.event_id is None:  # Should not be None due to default_factory
            self.event_id = uuid.uuid4()
        if self.timestamp is None:  # Should not be None due to default_factory
            self.timestamp = datetime.now(UTC)
