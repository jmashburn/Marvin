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

    # ==========================================================================
    # System Events
    # ==========================================================================
    test_message = auto()
    """A test message event, used for verifying notifier configurations."""
    webhook_task = auto()
    """An event that triggers scheduled webhook processing."""

    # ==========================================================================
    # User & Authentication Events
    # ==========================================================================
    user_signup = auto()
    """Event dispatched when a new user signs up."""
    user_authenticated = auto()
    """Event dispatched when a user authenticates."""
    user_updated = auto()
    """Event dispatched when a user profile is updated."""
    user_deleted = auto()
    """Event dispatched when a user account is deleted."""
    user_password_reset_requested = auto()
    """Event dispatched when a user requests a password reset."""
    user_password_reset_completed = auto()
    """Event dispatched when a user completes a password reset."""
    token_refreshed = auto()
    """Event dispatched when a user's access token is refreshed."""

    # ==========================================================================
    # Workspace Lifecycle Events
    # ==========================================================================
    workspace_created = auto()
    """Event dispatched when a new workspace is created."""
    workspace_updated = auto()
    """Event dispatched when a workspace is updated."""
    workspace_deleted = auto()
    """Event dispatched when a workspace is deleted."""
    workspace_activated = auto()
    """Event dispatched when a user switches to a different workspace."""
    workspace_settings_changed = auto()
    """Event dispatched when workspace preferences/settings are modified."""

    # ==========================================================================
    # Workspace Member Events
    # ==========================================================================
    member_added = auto()
    """Event dispatched when a new member is added to a workspace."""
    member_removed = auto()
    """Event dispatched when a member is removed from a workspace."""
    member_role_changed = auto()
    """Event dispatched when a member's role is changed."""

    # ==========================================================================
    # Invitation Events
    # ==========================================================================
    invitation_created = auto()
    """Event dispatched when a workspace invitation is created."""
    invitation_sent = auto()
    """Event dispatched when a workspace invitation is sent via email."""
    invitation_accepted = auto()
    """Event dispatched when a workspace invitation is accepted."""
    invitation_revoked = auto()
    """Event dispatched when a workspace invitation is revoked."""

    # ==========================================================================
    # Email Template Events
    # ==========================================================================
    email_template_created = auto()
    """Event dispatched when an email template is created."""
    email_template_updated = auto()
    """Event dispatched when an email template is updated."""
    email_template_deleted = auto()
    """Event dispatched when an email template is deleted."""

    # ==========================================================================
    # Entry Events (Content Management)
    # ==========================================================================
    entry_created = auto()
    """Event dispatched when a new entry is created."""
    entry_updated = auto()
    """Event dispatched when an entry is updated."""
    entry_deleted = auto()
    """Event dispatched when an entry is deleted."""
    entry_published = auto()
    """Event dispatched when an entry is published."""
    entry_unpublished = auto()
    """Event dispatched when an entry is unpublished."""
    entry_archived = auto()
    """Event dispatched when an entry is archived."""
    entry_restored = auto()
    """Event dispatched when an archived entry is restored."""

    # ==========================================================================
    # Form Events
    # ==========================================================================
    form_created = auto()
    """Event dispatched when a new form is created."""
    form_updated = auto()
    """Event dispatched when a form is updated."""
    form_deleted = auto()
    """Event dispatched when a form is deleted."""
    form_published = auto()
    """Event dispatched when a form is published."""
    form_archived = auto()
    """Event dispatched when a form is archived."""
    form_submission_received = auto()
    """Event dispatched when a form submission is received."""
    form_submission_processed = auto()
    """Event dispatched when a form submission is processed."""
    form_submission_failed = auto()
    """Event dispatched when a form submission fails."""

    # ==========================================================================
    # Collection Events
    # ==========================================================================
    collection_created = auto()
    """Event dispatched when a new collection is created."""
    collection_updated = auto()
    """Event dispatched when a collection is updated."""
    collection_deleted = auto()
    """Event dispatched when a collection is deleted."""
    entry_added_to_collection = auto()
    """Event dispatched when an entry is added to a collection."""
    entry_removed_from_collection = auto()
    """Event dispatched when an entry is removed from a collection."""

    # ==========================================================================
    # Asset Events (Media Management)
    # ==========================================================================
    asset_uploaded = auto()
    """Event dispatched when a new asset is uploaded."""
    asset_updated = auto()
    """Event dispatched when an asset metadata is updated."""
    asset_deleted = auto()
    """Event dispatched when an asset is deleted."""
    asset_attached_to_entry = auto()
    """Event dispatched when an asset is attached to an entry."""
    asset_detached_from_entry = auto()
    """Event dispatched when an asset is detached from an entry."""

    # ==========================================================================
    # Entry Type Events (Schema Management)
    # ==========================================================================
    entry_type_created = auto()
    """Event dispatched when a new entry type is created."""
    entry_type_updated = auto()
    """Event dispatched when an entry type is updated."""
    entry_type_deleted = auto()
    """Event dispatched when an entry type is deleted."""

    # ==========================================================================
    # Publishing Events
    # ==========================================================================
    site_published = auto()
    """Event dispatched when a site is published/deployed."""
    site_deployment_started = auto()
    """Event dispatched when a site deployment begins."""
    site_deployment_completed = auto()
    """Event dispatched when a site deployment completes."""
    site_deployment_failed = auto()
    """Event dispatched when a site deployment fails."""
    site_build_started = auto()
    """Event dispatched when a site build process starts."""
    site_build_completed = auto()
    """Event dispatched when a site build process completes."""
    site_build_failed = auto()
    """Event dispatched when a site build process fails."""

    # ==========================================================================
    # Webhook Events
    # ==========================================================================
    webhook_created = auto()
    """Event dispatched when a new webhook is created."""
    webhook_updated = auto()
    """Event dispatched when a webhook is updated."""
    webhook_deleted = auto()
    """Event dispatched when a webhook is deleted."""
    webhook_triggered = auto()
    """Event dispatched when a webhook is triggered."""
    webhook_delivery_succeeded = auto()
    """Event dispatched when a webhook delivery succeeds."""
    webhook_delivery_failed = auto()
    """Event dispatched when a webhook delivery fails."""

    # ==========================================================================
    # API & Integration Events
    # ==========================================================================
    api_token_created = auto()
    """Event dispatched when a new API token is created."""
    api_token_rotated = auto()
    """Event dispatched when an API token is rotated."""
    api_token_revoked = auto()
    """Event dispatched when an API token is revoked."""
    api_rate_limit_exceeded = auto()
    """Event dispatched when an API rate limit is exceeded."""
    api_client_created = auto()
    """Event dispatched when a new API client is registered."""
    api_client_updated = auto()
    """Event dispatched when an API client is updated."""
    api_client_deleted = auto()
    """Event dispatched when an API client is deleted."""
    api_client_token_rotated = auto()
    """Event dispatched when an API client token is rotated."""
    api_client_enabled = auto()
    """Event dispatched when an API client is enabled."""
    api_client_disabled = auto()
    """Event dispatched when an API client is disabled."""

    # ==========================================================================
    # Resource Events
    # ==========================================================================
    resource_created = auto()
    """Event dispatched when a new resource is created."""
    resource_updated = auto()
    """Event dispatched when a resource is updated."""
    resource_deleted = auto()
    """Event dispatched when a resource is deleted."""

    # ==========================================================================
    # Collaboration Events
    # ==========================================================================
    comment_added = auto()
    """Event dispatched when a comment is added to an entry."""
    comment_updated = auto()
    """Event dispatched when a comment is updated."""
    comment_deleted = auto()
    """Event dispatched when a comment is deleted."""
    entry_shared = auto()
    """Event dispatched when an entry is shared with another user."""
    mention_created = auto()
    """Event dispatched when a user is mentioned in content."""

    # ==========================================================================
    # Workflow & Automation Events
    # ==========================================================================
    workflow_started = auto()
    """Event dispatched when an automated workflow starts."""
    workflow_completed = auto()
    """Event dispatched when an automated workflow completes."""
    workflow_failed = auto()
    """Event dispatched when an automated workflow fails."""
    approval_requested = auto()
    """Event dispatched when content approval is requested."""
    approval_granted = auto()
    """Event dispatched when content approval is granted."""
    approval_rejected = auto()
    """Event dispatched when content approval is rejected."""

    # ==========================================================================
    # Scheduled Task Events
    # ==========================================================================
    scheduled_task_created = auto()
    """Event dispatched when a scheduled task is created."""
    scheduled_task_updated = auto()
    """Event dispatched when a scheduled task is updated."""
    scheduled_task_deleted = auto()
    """Event dispatched when a scheduled task is deleted."""
    scheduled_task_triggered = auto()
    """Event dispatched when a scheduled task is triggered by the scheduler."""
    scheduled_task_started = auto()
    """Event dispatched when a scheduled task starts execution."""
    scheduled_task_completed = auto()
    """Event dispatched when a scheduled task completes successfully."""
    scheduled_task_failed = auto()
    """Event dispatched when a scheduled task execution fails."""
    scheduled_task_cancelled = auto()
    """Event dispatched when a scheduled task execution is cancelled."""

    # ==========================================================================
    # Search & Indexing Events
    # ==========================================================================
    search_index_updated = auto()
    """Event dispatched when the search index is updated."""
    search_index_rebuilt = auto()
    """Event dispatched when the search index is completely rebuilt."""

    # ==========================================================================
    # Security & Audit Events
    # ==========================================================================
    permission_changed = auto()
    """Event dispatched when permissions are changed."""
    role_assigned = auto()
    """Event dispatched when a role is assigned to a user."""
    role_revoked = auto()
    """Event dispatched when a role is revoked from a user."""
    suspicious_activity_detected = auto()
    """Event dispatched when suspicious activity is detected."""
    login_failed_multiple_times = auto()
    """Event dispatched when multiple login failures occur."""
    session_expired = auto()
    """Event dispatched when a user session expires."""

    # ==========================================================================
    # Storage & Backup Events
    # ==========================================================================
    backup_started = auto()
    """Event dispatched when a backup process starts."""
    backup_completed = auto()
    """Event dispatched when a backup process completes."""
    backup_failed = auto()
    """Event dispatched when a backup process fails."""
    storage_quota_warning = auto()
    """Event dispatched when storage quota reaches warning threshold."""
    storage_quota_exceeded = auto()
    """Event dispatched when storage quota is exceeded."""

    # ==========================================================================
    # Notification Events
    # ==========================================================================
    notification_sent = auto()
    """Event dispatched when a notification is sent to a user."""
    notification_read = auto()
    """Event dispatched when a user reads a notification."""
    digest_sent = auto()
    """Event dispatched when a digest email is sent."""


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
    workspace = "workspace"
    """Indicates the event data pertains to a workspace entity."""
    entry = "entry"
    """Indicates the event data pertains to an entry entity."""
    form = "form"
    """Indicates the event data pertains to a form entity."""
    form_submission = "form_submission"
    """Indicates the event data pertains to a form submission entity."""
    collection = "collection"
    """Indicates the event data pertains to a collection entity."""
    asset = "asset"
    """Indicates the event data pertains to an asset entity."""
    webhook = "webhook"
    """Indicates the event data pertains to a webhook entity."""
    member = "member"
    """Indicates the event data pertains to a workspace member."""
    invitation = "invitation"
    """Indicates the event data pertains to an invitation."""
    api_token = "api_token"
    """Indicates the event data pertains to an API token."""
    api_client = "api_client"
    """Indicates the event data pertains to an API client."""
    entry_type = "entry_type"
    """Indicates the event data pertains to an entry type."""
    resource = "resource"
    """Indicates the event data pertains to a resource."""
    deployment = "deployment"
    """Indicates the event data pertains to a site deployment."""


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


class EventWorkspaceCreatedData(EventDocumentDataBase):
    """
    Data payload for an event indicating a workspace has been created.
    """

    document_type: EventDocumentTypeBase = EventDocumentType.generic
    operation: EventOperationBase = EventOperation.create
    workspace_id: UUID4
    """The unique identifier of the created workspace."""
    workspace_name: str
    """The name of the created workspace."""
    creator_id: UUID4
    """The user ID of the workspace creator."""


class EventWorkspaceData(EventDocumentDataBase):
    """Data payload for workspace-related events (updates, settings changes)."""

    document_type: EventDocumentTypeBase = EventDocumentType.workspace
    workspace_id: UUID4
    """The unique identifier of the workspace."""
    workspace_name: str
    """The name of the workspace."""
    workspace_slug: str
    """The slug of the workspace."""


class EventWorkspaceSettingsData(EventDocumentDataBase):
    """Data payload for workspace settings/preferences change events."""

    document_type: EventDocumentTypeBase = EventDocumentType.workspace
    workspace_id: UUID4
    """The unique identifier of the workspace."""
    changed_fields: list[str]
    """List of preference fields that were modified (e.g., ['site_title', 'site_logo'])."""


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


# =============================================================================
# Entry Event Data Models
# =============================================================================


class EventEntryData(EventDocumentDataBase):
    """Data payload for entry-related events."""

    document_type: EventDocumentTypeBase = EventDocumentType.entry
    entry_id: UUID4
    """The unique identifier of the entry."""
    entry_title: str
    """The title of the entry."""
    entry_type: str | None = None
    """The type/schema of the entry."""
    workspace_id: UUID4
    """The workspace containing the entry."""
    author_id: UUID4
    """The user who created/modified the entry."""


class EventFormData(EventDocumentDataBase):
    """Data payload for form-related events."""

    document_type: EventDocumentTypeBase = EventDocumentType.form
    operation: "EventOperation"
    """The operation performed on the form."""
    form_id: UUID4
    """The unique identifier of the form."""
    form_name: str
    """The name of the form."""
    workspace_id: UUID4
    """The workspace containing the form."""


class EventFormSubmissionData(EventDocumentDataBase):
    """Data payload for form submission events."""

    document_type: EventDocumentTypeBase = EventDocumentType.form_submission
    operation: "EventOperation"
    """The operation performed."""
    form_id: UUID4
    """The unique identifier of the form."""
    form_name: str
    """The name of the form."""
    submission_id: UUID4 | None
    """The unique identifier of the submission (if persisted)."""
    submission_data: dict
    """The submitted form data."""
    workspace_id: UUID4
    """The workspace containing the form."""


class EventCollectionData(EventDocumentDataBase):
    """Data payload for collection-related events."""

    document_type: EventDocumentTypeBase = EventDocumentType.collection
    collection_id: UUID4
    """The unique identifier of the collection."""
    collection_name: str
    """The name of the collection."""
    workspace_id: UUID4
    """The workspace containing the collection."""
    entry_count: int | None = None
    """The number of entries in the collection."""


class EventAssetData(EventDocumentDataBase):
    """Data payload for asset-related events."""

    document_type: EventDocumentTypeBase = EventDocumentType.asset
    asset_id: UUID4
    """The unique identifier of the asset."""
    slug: str
    """The asset slug."""
    name: str
    """The asset name."""
    mime_type: str
    """The MIME type of the asset."""
    asset_type: str
    """The asset type classification (image, document, video, audio, archive, svg, other)."""
    storage_key: str
    """The storage key for the asset."""

    @classmethod
    def from_schema(cls, asset: "AssetRead") -> "EventAssetData":
        """
        Create EventAssetData from an AssetRead schema.

        Args:
            asset: AssetRead schema instance

        Returns:
            EventAssetData instance
        """
        from marvin.schemas.platform.assets import AssetRead

        return cls(
            operation=EventOperation.info,
            asset_id=asset.id,
            slug=asset.slug,
            name=asset.name,
            mime_type=asset.mime_type,
            asset_type=asset.asset_type,
            storage_key=asset.storage_key,
        )


class EventMemberData(EventDocumentDataBase):
    """Data payload for workspace member events."""

    document_type: EventDocumentTypeBase = EventDocumentType.member
    workspace_id: UUID4
    """The workspace ID."""
    user_id: UUID4
    """The user ID of the member."""
    username: str
    """The username of the member."""
    role: str
    """The role of the member (OWNER, ADMIN, EDITOR, AUTHOR, VIEWER)."""
    previous_role: str | None = None
    """The previous role (for role change events)."""


class EventInvitationData(EventDocumentDataBase):
    """Data payload for invitation events."""

    document_type: EventDocumentTypeBase = EventDocumentType.invitation
    invitation_id: UUID4 | str
    """The unique identifier or token of the invitation."""
    workspace_id: UUID4
    """The workspace the invitation is for."""
    inviter_id: UUID4
    """The user who created the invitation."""
    invitee_email: str | None = None
    """The email address of the invited user (if applicable)."""
    invitation_url: str | None = None
    """The URL the invitee clicks to accept the invitation."""
    uses_left: int | None = None
    """The number of remaining uses for the invitation."""


class EventAPITokenData(EventDocumentDataBase):
    """Data payload for API token events."""

    document_type: EventDocumentTypeBase = EventDocumentType.api_token
    token_id: UUID4
    """The unique identifier of the API token."""
    token_name: str
    """The name of the API token."""
    user_id: UUID4
    """The user who owns the token."""
    token_prefix: str | None = None
    """The prefix of the token (for identification)."""


class EventDeploymentData(EventDocumentDataBase):
    """Data payload for site deployment events."""

    document_type: EventDocumentTypeBase = EventDocumentType.deployment
    workspace_id: UUID4
    """The workspace being deployed."""
    deployment_id: str | None = None
    """The unique identifier of the deployment."""
    site_url: str | None = None
    """The URL of the deployed site."""
    triggered_by: UUID4
    """The user who triggered the deployment."""
    status: str | None = None
    """The status of the deployment (started, completed, failed)."""
    error_message: str | None = None
    """Error message if deployment failed."""


class EventAPIClientData(EventDocumentDataBase):
    """Data payload for API client events."""

    document_type: EventDocumentTypeBase = EventDocumentType.api_client
    api_client_id: UUID4
    """The unique identifier of the API client."""
    api_client_name: str
    """The name of the API client."""
    api_client_slug: str
    """The slug of the API client."""
    workspace_id: UUID4
    """The workspace the API client belongs to."""
    permissions: dict
    """The permissions granted to the API client."""
    enabled: bool
    """Whether the API client is enabled."""
    token_prefix: str | None = None
    """The prefix of the token (for token rotation events)."""


class EventEntryTypeData(EventDocumentDataBase):
    """Data payload for entry type events."""

    document_type: EventDocumentTypeBase = EventDocumentType.entry_type
    entry_type_id: UUID4
    """The unique identifier of the entry type."""
    entry_type_name: str
    """The name of the entry type."""
    entry_type_slug: str
    """The slug of the entry type."""
    workspace_id: UUID4
    """The workspace the entry type belongs to."""
    description: str | None = None
    """The description of the entry type."""


class EventResourceData(EventDocumentDataBase):
    """Data payload for resource events."""

    document_type: EventDocumentTypeBase = EventDocumentType.resource
    resource_id: UUID4
    """The unique identifier of the resource."""
    resource_name: str
    """The name of the resource."""
    resource_slug: str
    """The slug of the resource."""
    resource_type: str
    """The type of resource (fabric, tool, supplier, etc.)."""
    workspace_id: UUID4
    """The workspace the resource belongs to."""
    url: str | None = None
    """The external URL of the resource."""


class EventScheduledTaskData(EventDocumentDataBase):
    """Data payload for scheduled task events."""

    document_type: EventDocumentTypeBase = EventDocumentType.generic
    task_id: UUID4
    """The unique identifier of the scheduled task."""
    task_name: str
    """The name of the scheduled task."""
    task_slug: str
    """The slug of the scheduled task."""
    task_type: str
    """The type of task (e.g., 'publish', 'cleanup')."""
    workspace_id: UUID4 | None = None
    """The workspace the task belongs to (None for system tasks)."""
    enabled: bool = True
    """Whether the task is enabled."""
    next_run_at: datetime | None = None
    """Next scheduled execution time."""
    last_status: str | None = None
    """Status of last execution."""

    @classmethod
    def from_model(cls, task: "ScheduledTaskModel") -> "EventScheduledTaskData":
        """
        Create EventScheduledTaskData from a ScheduledTaskModel.

        Args:
            task: ScheduledTaskModel instance

        Returns:
            EventScheduledTaskData instance
        """
        from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel

        return cls(
            operation=EventOperation.info,
            task_id=task.id,
            task_name=task.name,
            task_slug=task.slug,
            task_type=task.task_type,
            workspace_id=task.group_id,
            enabled=task.enabled,
            next_run_at=task.next_run_at,
            last_status=task.last_status,
        )


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

    # Core identifiers for audit and filtering
    workspace_id: UUID4
    """The workspace this event pertains to."""
    user_id: UUID4 | None = None
    """The user who triggered this event (None for system events)."""
    entity_id: UUID4 | None = None
    """The ID of the primary entity this event is about (entry, asset, etc.)."""
    entity_type: str | None = None
    """The type of the primary entity (entry, asset, workspace, etc.)."""

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
