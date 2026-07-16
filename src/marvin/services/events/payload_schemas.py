"""
Maps event types to their real webhook payload structure.

Builds example payloads from the actual EventDocumentDataBase subclasses
so the Connect webhook page shows exactly what will be received.
"""

from marvin.services.event_bus_service.event_types import (
    EventInvitationData,
    EventEntryData,
    EventAssetData,
    EventFormSubmissionData,
    EventDocumentDataBase,
    EventOperation,
    EventDocumentType,
    EventScheduledTaskData,
    EventWorkspaceData,
)
from marvin.core.root_logger import get_logger

logger = get_logger(__name__)

# Wrapper showing the full webhook payload structure
PAYLOAD_WRAPPER = {
    "eventType": "<event_type_name>",
    "eventId": "evt_a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "timestamp": "2026-07-16T00:00:00Z",
    "workspaceId": "<workspace-uuid>",
    "integrationId": "<integration-name>",
    "message": {
        "title": "<Event Label>",
        "body": "<event description>",
    },
    "documentData": {},  # replaced per event type
}

# Example values per field name — used to populate example payloads
FIELD_EXAMPLES = {
    "invitation_token": "abc123token",
    "workspace_id": "<workspace-uuid>",
    "workspace_name": "My Workspace",
    "inviter_name": "Jane Smith",
    "invitee_email": "user@example.com",
    "invitation_url": "https://yoursite.com/register?token=abc123",
    "uses_left": 5,
    "entry_id": "<entry-uuid>",
    "entry_title": "My Blog Post",
    "entry_type": "post",
    "author_id": "<user-uuid>",
    "asset_id": "<asset-uuid>",
    "asset_name": "photo.jpg",
    "asset_type": "image/jpeg",
    "form_id": "<form-uuid>",
    "form_name": "Contact Form",
    "submission_id": "<submission-uuid>",
    "task_id": "<task-uuid>",
    "task_name": "Daily Cleanup",
    "task_type": "cleanup_temp_files",
    "operation": "info",
    "document_type": "entry",
}


def get_payload_example(event_type: str) -> dict:
    """Build an example webhook payload for the given event type."""
    from marvin.services.event_bus_service.event_types import EventTypes

    # Map event type names to their document data classes and example values
    doc_data_map = {
        "invitation_sent": {
            "documentType": "invitation",
            "operation": "info",
            "invitationToken": "abc123token",
            "workspaceId": "<workspace-uuid>",
            "workspaceName": "My Workspace",
            "inviterName": "Jane Smith",
            "inviteeEmail": "user@example.com",
            "invitationUrl": "https://yoursite.com/register?token=abc123",
            "usesLeft": 5,
        },
        "invitation_created": {
            "documentType": "invitation",
            "operation": "create",
            "invitationToken": "abc123token",
            "workspaceId": "<workspace-uuid>",
            "workspaceName": "My Workspace",
            "inviterName": "Jane Smith",
            "usesLeft": 10,
        },
        "invitation_accepted": {
            "documentType": "invitation",
            "operation": "update",
            "invitationToken": "abc123token",
            "workspaceId": "<workspace-uuid>",
            "workspaceName": "My Workspace",
            "inviterName": "Jane Smith",
        },
        "member_added": {
            "documentType": "workspace",
            "operation": "create",
            "workspaceId": "<workspace-uuid>",
            "workspaceName": "My Workspace",
            "workspaceSlug": "my-workspace",
        },
        "entry_published": {
            "documentType": "entry",
            "operation": "publish",
            "entryId": "<entry-uuid>",
            "entryTitle": "My Blog Post",
            "entryType": "post",
            "workspaceId": "<workspace-uuid>",
            "authorId": "<user-uuid>",
        },
        "entry_created": {
            "documentType": "entry",
            "operation": "create",
            "entryId": "<entry-uuid>",
            "entryTitle": "Draft Post",
            "entryType": "post",
            "workspaceId": "<workspace-uuid>",
            "authorId": "<user-uuid>",
        },
        "asset_uploaded": {
            "documentType": "asset",
            "operation": "create",
            "assetId": "<asset-uuid>",
            "assetName": "photo.jpg",
            "workspaceId": "<workspace-uuid>",
        },
        "form_submission_received": {
            "documentType": "form_submission",
            "operation": "create",
            "formId": "<form-uuid>",
            "formName": "Contact Form",
            "submissionId": "<submission-uuid>",
            "workspaceId": "<workspace-uuid>",
        },
        "scheduled_task_completed": {
            "documentType": "generic",
            "operation": "info",
            "taskId": "<task-uuid>",
            "taskName": "Daily Cleanup",
            "taskType": "cleanup_temp_files",
            "workspaceId": "<workspace-uuid>",
        },
    }

    doc_data = doc_data_map.get(event_type, {
        "documentType": "generic",
        "operation": "info",
        "workspaceId": "<workspace-uuid>",
    })

    # Find label from EventTypes if possible
    try:
        et = EventTypes[event_type]
        label = event_type.replace("_", " ").title()
    except KeyError:
        label = event_type.replace("_", " ").title()

    return {
        "eventType": event_type,
        "eventId": "851a54f3-bc85-4123-aa35-7c139db2cb59",
        "timestamp": "2026-07-16T00:34:37Z",
        "workspaceId": "<workspace-uuid>",
        "integrationId": "marvin_integration",
        "message": {
            "title": label,
            "body": f"Event: {event_type}",
        },
        "documentData": doc_data,
    }
