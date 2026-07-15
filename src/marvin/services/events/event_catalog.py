"""
Event catalog — defines user-subscribable events with their data contracts.

Each entry describes:
  - name: human-readable event name
  - description: what triggers this event
  - category: grouping for the UI
  - variables: {{slug}} values available in templates/notifications
  - enabled: whether this event is available for subscription
"""

from dataclasses import dataclass, field


@dataclass
class EventVariable:
    slug: str
    description: str
    example: str


@dataclass
class CatalogEntry:
    event_type: str       # matches EventTypes enum value name
    name: str
    description: str
    category: str
    variables: list[EventVariable] = field(default_factory=list)
    enabled: bool = True


COMMON_VARS = [
    EventVariable("workspace_name", "Name of the workspace", "My Blog"),
]

CATALOG: list[CatalogEntry] = [
    # ── Invitations ─────────────────────────────────────────────────────────
    CatalogEntry(
        event_type="invitation_sent",
        name="Invitation Sent",
        description="A user has been invited to join the workspace.",
        category="Members",
        variables=COMMON_VARS + [
            EventVariable("invitation_url", "Link for the recipient to accept the invite", "https://..."),
            EventVariable("inviter_name", "Name of the person who sent the invite", "Jane Smith"),
            EventVariable("recipient_email", "Email address of the invited user", "user@example.com"),
        ],
    ),
    CatalogEntry(
        event_type="invitation_accepted",
        name="Invitation Accepted",
        description="A user accepted their workspace invitation.",
        category="Members",
        variables=COMMON_VARS + [
            EventVariable("username", "Username of the new member", "jsmith"),
            EventVariable("first_name", "First name of the new member", "Jane"),
        ],
    ),

    # ── Members ─────────────────────────────────────────────────────────────
    CatalogEntry(
        event_type="member_added",
        name="Member Added",
        description="A new member joined the workspace.",
        category="Members",
        variables=COMMON_VARS + [
            EventVariable("username", "Username of the new member", "jsmith"),
            EventVariable("first_name", "First name of the new member", "Jane"),
        ],
    ),
    CatalogEntry(
        event_type="member_removed",
        name="Member Removed",
        description="A member was removed from the workspace.",
        category="Members",
        variables=COMMON_VARS + [
            EventVariable("username", "Username of the removed member", "jsmith"),
        ],
    ),

    # ── Auth ────────────────────────────────────────────────────────────────
    CatalogEntry(
        event_type="user_signup",
        name="New User Signup",
        description="A new user account was created.",
        category="Authentication",
        variables=COMMON_VARS + [
            EventVariable("username", "Username of the new user", "jsmith"),
            EventVariable("first_name", "First name", "Jane"),
            EventVariable("login_url", "Link to log in", "https://..."),
        ],
    ),
    CatalogEntry(
        event_type="user_password_reset_requested",
        name="Password Reset Requested",
        description="A user requested a password reset.",
        category="Authentication",
        variables=[
            EventVariable("username", "Username requesting the reset", "jsmith"),
            EventVariable("reset_url", "Password reset link", "https://..."),
            EventVariable("expiry_hours", "Hours until the link expires", "24"),
        ],
    ),
    CatalogEntry(
        event_type="user_password_reset_completed",
        name="Password Reset Completed",
        description="A user successfully reset their password.",
        category="Authentication",
        variables=[
            EventVariable("username", "Username who completed the reset", "jsmith"),
        ],
    ),

    # ── Content ─────────────────────────────────────────────────────────────
    CatalogEntry(
        event_type="entry_published",
        name="Entry Published",
        description="A content entry was published.",
        category="Content",
        variables=COMMON_VARS + [
            EventVariable("entry_title", "Title of the published entry", "My Post"),
            EventVariable("entry_slug", "URL slug of the entry", "my-post"),
            EventVariable("author_name", "Author's display name", "Jane Smith"),
            EventVariable("entry_url", "Public URL of the entry", "https://..."),
        ],
    ),
    CatalogEntry(
        event_type="entry_created",
        name="Entry Created",
        description="A new content entry was created.",
        category="Content",
        variables=COMMON_VARS + [
            EventVariable("entry_title", "Title of the entry", "Draft Post"),
            EventVariable("author_name", "Author's display name", "Jane Smith"),
        ],
    ),
    CatalogEntry(
        event_type="entry_updated",
        name="Entry Updated",
        description="A content entry was updated.",
        category="Content",
        variables=COMMON_VARS + [
            EventVariable("entry_title", "Title of the entry", "My Post"),
            EventVariable("author_name", "Who made the update", "Jane Smith"),
        ],
    ),

    # ── Forms ────────────────────────────────────────────────────────────────
    CatalogEntry(
        event_type="form_submission_received",
        name="Form Submission Received",
        description="Someone submitted a form in the workspace.",
        category="Forms",
        variables=COMMON_VARS + [
            EventVariable("form_name", "Name of the form", "Contact Form"),
            EventVariable("submitter_email", "Email of the submitter (if provided)", "user@example.com"),
        ],
    ),

    # ── Deployments ──────────────────────────────────────────────────────────
    CatalogEntry(
        event_type="site_deployment_completed",
        name="Site Deployment Completed",
        description="A site deployment finished successfully.",
        category="Publishing",
        variables=COMMON_VARS + [
            EventVariable("site_url", "URL of the deployed site", "https://mysite.com"),
            EventVariable("duration", "How long the deployment took", "45s"),
        ],
    ),
    CatalogEntry(
        event_type="site_deployment_failed",
        name="Site Deployment Failed",
        description="A site deployment failed.",
        category="Publishing",
        variables=COMMON_VARS + [
            EventVariable("error_message", "What went wrong", "Build timeout"),
        ],
    ),
    CatalogEntry(
        event_type="site_build_failed",
        name="Site Build Failed",
        description="A site build failed.",
        category="Publishing",
        variables=COMMON_VARS + [
            EventVariable("error_message", "What went wrong", "Compilation error"),
        ],
    ),

    # ── Storage ──────────────────────────────────────────────────────────────
    CatalogEntry(
        event_type="storage_quota_warning",
        name="Storage Quota Warning",
        description="Storage usage is approaching the limit.",
        category="System",
        variables=COMMON_VARS + [
            EventVariable("usage_percent", "Percentage of quota used", "85"),
            EventVariable("used_gb", "GB currently used", "8.5"),
            EventVariable("quota_gb", "Total quota in GB", "10"),
        ],
    ),
    CatalogEntry(
        event_type="storage_quota_exceeded",
        name="Storage Quota Exceeded",
        description="Storage quota has been exceeded.",
        category="System",
        variables=COMMON_VARS + [
            EventVariable("usage_percent", "Percentage of quota used", "103"),
        ],
    ),

    # ── Scheduled Tasks ───────────────────────────────────────────────────────
    CatalogEntry(
        event_type="scheduled_task_failed",
        name="Scheduled Task Failed",
        description="A scheduled task failed to execute.",
        category="Automation",
        variables=COMMON_VARS + [
            EventVariable("task_name", "Name of the failed task", "Daily Cleanup"),
            EventVariable("error_message", "What went wrong", "Connection timeout"),
        ],
    ),
    CatalogEntry(
        event_type="scheduled_task_completed",
        name="Scheduled Task Completed",
        description="A scheduled task ran successfully.",
        category="Automation",
        variables=COMMON_VARS + [
            EventVariable("task_name", "Name of the task", "Daily Cleanup"),
            EventVariable("duration_ms", "How long it took (ms)", "1234"),
        ],
    ),
]

# Quick lookup
CATALOG_BY_TYPE: dict[str, CatalogEntry] = {e.event_type: e for e in CATALOG}

# Categories in display order
CATEGORIES = ["Members", "Authentication", "Content", "Forms", "Publishing", "Automation", "System"]


def get_event_variables(event_type: str) -> list[EventVariable]:
    """Return variables available for a given event type."""
    entry = CATALOG_BY_TYPE.get(event_type)
    return entry.variables if entry else []


def get_catalog_entry(event_type: str) -> CatalogEntry | None:
    return CATALOG_BY_TYPE.get(event_type)
