"""
This module defines Pydantic schemas related to group-specific event notification
configurations within the Marvin application.

It includes schemas for:
- Defining and managing the specific notification event options that a group notifier
  is subscribed to (e.g., which system events should trigger this notifier).
- Creating, updating, and representing the group event notifiers themselves,
  which typically include details like a name, an Apprise URL for sending
  notifications, and the set of active event options.
"""

from pydantic import UUID4, ConfigDict  # HttpUrl imported but not used directly in this file's models

# SQLAlchemy ORM imports for loader_options method.
# These are relevant for optimizing database queries when fetching related data.
from sqlalchemy.orm import joinedload

# from sqlalchemy.orm import selectinload # selectinload imported but not used
from sqlalchemy.orm.interfaces import LoaderOption

# Corresponding SQLAlchemy models (used in loader_options)
from marvin.db.models.groups import (
    GroupEventNotifierModel,
)  # , GroupEventNotifierOptionsModel # Latter not directly used here
from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model
from marvin.schemas.response.pagination import PaginationBase  # Base for pagination responses

# =============================================================================
# Group Events Notifier Options Schemas
# These schemas define the specific event options linked to a group's notifier.
# =============================================================================


class GroupEventNotifierOptions(_MarvinModel):
    """
    Represents a set of configurable event options for a group notifier.

    This schema might define boolean flags for various system events, indicating
    whether a specific group notifier should be triggered by those events.
    The docstring implies these should align with `EventTypes` from the EventBusService.
    """

    test: bool = True
    """
    Example field: Indicates if the 'test' event type is active for this notifier.
    This is likely a placeholder; actual event types (e.g., `user_created`, `task_completed`)
    would be defined as boolean fields here.
    """


class GroupEventNotifierOptionsCreate(_MarvinModel):
    """
    Schema for creating a link between a group notifier and a system event option.
    This typically represents subscribing a group notifier to a specific event.
    """

    namespace: str
    """The namespace of the system event (e.g., "core", "user_events")."""
    slug: str
    """The slug identifying the specific system event within the namespace (e.g., "test-message", "user_signup")."""
    # Potentially an `enabled: bool = True` field could be here if options can be individually toggled
    # for a specific notifier, beyond just system-wide enablement of the EventNotifierOption itself.


class GroupEventNotifierOptionsUpdate(GroupEventNotifierOptionsCreate):
    """
    Schema for updating a group event notifier option link.
    Currently identical to create, but includes ID for targeting the update.
    """

    id: UUID4
    """The unique identifier of the group event notifier option link to update."""
    # Inherits namespace, slug from Create. Update might involve changing these or other attributes like 'enabled'.


class GroupEventNotifierOptionsRead(GroupEventNotifierOptionsCreate):
    """
    Schema for reading a group event notifier option link.
    Represents an active subscription of a group notifier to a system event.
    """

    # Inherits namespace, slug from Create.
    model_config = ConfigDict(from_attributes=True)  # Allows ORM mode / creating from attributes


class GroupEventNotifierOptionsSummary(_MarvinModel):
    """
    Schema for a summary representation of a group event notifier option.
    Provides a combined `option` string (namespace.slug).
    """

    option: str
    """A combined string, typically "namespace.slug", uniquely identifying the subscribed event option."""
    model_config = ConfigDict(from_attributes=True)


class GroupEventNotifierOptionsPagination(PaginationBase):
    """
    Schema for paginated responses containing a list of group event notifier option summaries.
    """

    items: list[GroupEventNotifierOptionsSummary]
    """The list of group event notifier option summaries for the current page."""


# =======================================================================
# Group Event Notifiers Schemas
# These schemas define the actual notifier configurations for a group.
# =======================================================================


class GroupEventNotifierCreate(_MarvinModel):
    """
    Schema for creating a new group event notifier.
    A notifier typically involves a service URL (e.g., Apprise) and a set of
    event options it should react to.
    """

    name: str
    """A user-defined name for this notifier configuration (e.g., "Slack Alerts", "Admin Email")."""
    apprise_url: str | None = None
    """
    The Apprise URL or similar service URL used to send notifications.
    Optional on creation, but likely required for the notifier to function.
    """
    options: list[str] = []  # Type hint changed to list[str]
    """
    A list of event option strings (e.g., ["core.test-message", "user.user_signup"])
    that this notifier should be subscribed to. These strings typically correspond
    to the `namespace.slug` of system-wide `EventNotifierOptionsModel` entries.
    """
    model_config = ConfigDict(
        from_attributes=True,  # Allows creating from ORM model attributes
        json_schema_extra={  # Provides an example for OpenAPI documentation
            "example": {
                "name": "My Project Updates Notifier",
                "apprise_url": "json://some-service-url/for/notifications",
                "options": ["core.test-message", "project.task_completed"],
            }
        },
    )


class GroupEventNotifierSave(GroupEventNotifierCreate):
    """
    Schema used internally, likely when saving a notifier, ensuring `group_id` is included.
    Extends `GroupEventNotifierCreate` with `group_id`.
    """

    group_id: UUID4
    """The ID of the group this event notifier belongs to."""
    # `options` field is inherited. The original `options: list = []` here might override
    # the `list[str]` from parent if not careful, but Pydantic usually handles inheritance well.
    # For clarity, ensuring it matches or relies on parent's definition.
    # If this schema is purely for DB saving and options are handled via relationship table,
    # this list might be transient for initial setup.


class GroupEventNotifierUpdate(GroupEventNotifierSave):  # Should ideally extend a base that doesn't mandate all create fields
    """
    Schema for updating an existing group event notifier.
    Extends `GroupEventNotifierSave`, implying all fields can be updated,
    and adds an `enabled` flag.

    For partial updates (PATCH), individual fields should be `Optional`.
    This schema implies a PUT-style update where all fields are provided.
    """

    # group_id is inherited, but typically not changed during an update of an existing notifier.
    # name, apprise_url, options are inherited.
    enabled: bool = True
    """Whether this notifier configuration is currently active. Defaults to True on update if not specified."""
    # `options: list = []` here again. If this is for *replacing* options, `list[str]` is appropriate.


class GroupEventNotifierRead(_MarvinModel):
    """
    Schema for representing a group event notifier when read from the system.
    Includes its configuration and the list of event options it's subscribed to.
    """

    id: UUID4
    """The unique identifier of the group event notifier."""
    name: str
    """The user-defined name of the notifier."""
    enabled: bool
    """Indicates if this notifier is currently active."""
    group_id: UUID4
    """The ID of the group this notifier belongs to."""
    options: list[GroupEventNotifierOptionsSummary] = []
    """
    A list of event option summaries that this notifier is subscribed to.
    Each summary typically includes the "namespace.slug" string.
    """
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        """
        Provides SQLAlchemy loader options for optimizing queries for this schema.

        Currently configures eager loading for the `options` relationship
        using `joinedload`, which helps prevent N+1 query problems when fetching
        notifiers along with their subscribed options.

        Returns:
            list[LoaderOption]: A list of SQLAlchemy loader options.
        """
        # Eagerly load the 'options' relationship when querying for GroupEventNotifierModel
        return [joinedload(GroupEventNotifierModel.options)]


class GroupEventNotifierPagination(PaginationBase):
    """
    Schema for paginated responses containing a list of group event notifiers.
    """

    items: list[GroupEventNotifierRead]
    """The list of group event notifiers for the current page."""


class GroupEventNotifierPrivate(GroupEventNotifierRead):
    """
    Schema for representing a group event notifier with potentially sensitive
    information, like the full `apprise_url`.

    Extends `GroupEventNotifierRead` and adds fields that should not typically
    be exposed in general listings but might be needed for specific operations
    (e.g., editing, testing the notifier).
    """

    apprise_url: str
    """
    The Apprise URL (or similar service URL) for sending notifications.
    This field is considered private and is not included in the standard `GroupEventNotifierRead`.
    """
    model_config = ConfigDict(from_attributes=True)
