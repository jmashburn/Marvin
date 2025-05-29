"""
This module defines Pydantic schemas related to system-wide event notifier options
within the Marvin application.

These schemas are used for creating, updating, reading, and paginating
event notifier options, which likely represent different types of notifications
that can be configured in the system (e.g., email on new user signup, webhook
on data update).
"""

from pydantic import UUID4, ConfigDict  # HttpUrl was imported but not used.

# sqlalchemy.orm imports (joinedload, selectinload, LoaderOption) and EventNotifierOptionsModel
# are not directly used in the Pydantic schema definitions here but might be relevant
# for ORM interactions elsewhere or intended for future use with loader_options in _MarvinModel.
# For now, they are considered unused in this specific file's context.
# from sqlalchemy.orm import joinedload, selectinload
# from sqlalchemy.orm.interfaces import LoaderOption
# from marvin.db.models.events import EventNotifierOptionsModel
from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model for Marvin schemas
from marvin.schemas.response.pagination import PaginationBase  # Base for pagination responses

# =============================================================================
# Events Notifier Options Schemas
# =============================================================================


class EventNotifierOptions(_MarvinModel):
    """
    Schema representing a collection of boolean flags for various event types.
    This model seems to define which events are generally available or configurable.

    The docstring mentions keeping these events in sync with `EventTypes`
    in the `EventBusService`. This suggests that each field here corresponds
    to a type of event that can trigger notifications.
    """

    # Example field, indicating if a 'test' event type is available/configurable.
    # More fields representing other event types would typically be present here.
    test: bool = True
    """Indicates if the 'test' event type is active or configurable.
       This is likely a placeholder or example; real event types would be fields here."""
    # e.g., user_signup: bool = True
    # e.g., item_created: bool = False


class EventNotifierOptionsCreate(_MarvinModel):
    """
    Schema for creating a new event notifier option in the system.
    This defines a specific type of notification that can occur.
    """

    name: str
    """Human-readable name for the event notifier option (e.g., "New User Email Notification")."""
    namespace: str
    """Namespace for the event option, helping to categorize it (e.g., "user", "system")."""
    description: str | None = None
    """Optional detailed description of what this event notifier option represents or does."""
    enabled: bool | None = False
    """Whether this notifier option is enabled by default upon creation. Defaults to False."""


class EventNotifierOptionsUpdate(EventNotifierOptionsCreate):
    """
    Schema for updating an existing event notifier option.
    Includes all fields from `EventNotifierOptionsCreate` and the ID of the option to update.
    """

    id: UUID4
    """The unique identifier of the event notifier option to update."""
    # `name`, `namespace`, `description`, `enabled` are inherited from EventNotifierOptionsCreate.
    # When updating, all fields are typically optional. Pydantic handles this if the model
    # fields themselves are marked Optional or have defaults in the update payload.
    # For a true PATCH-style update, fields in the instance should be Optional.


class EventNotifierOptionsRead(_MarvinModel):
    """
    Schema for representing an event notifier option when read from the system.
    This is a general representation, often used for detailed views.
    """

    name: str
    """Human-readable name of the event notifier option."""
    description: str | None  # Assuming description can be None if not provided during creation.
    """Detailed description of the event notifier option."""
    enabled: bool | None = False
    """Current status (enabled/disabled) of the event notifier option."""

    # Pydantic model configuration
    # `from_attributes=True` allows creating instances from ORM objects (e.g., SQLAlchemy models).
    model_config = ConfigDict(from_attributes=True)


class EventNotifierOptionsSummary(EventNotifierOptionsRead):
    """
    Schema for a summary representation of an event notifier option.
    Extends `EventNotifierOptionsRead` with a combined `option` field (namespace.slug).
    """

    option: str  # A combined string, typically "namespace.slug", representing the unique key of the option.
    # `name`, `description`, `enabled` are inherited.

    # Inherits model_config from EventNotifierOptionsRead.
    # model_config = ConfigDict(from_attributes=True) # Redundant if inherited and not changed.


class EventNotifierOptionsPagination(PaginationBase):
    """
    Schema for paginated responses containing a list of event notifier option summaries.
    """

    items: list[EventNotifierOptionsSummary]  # The list of event notifier option summaries for the current page.
