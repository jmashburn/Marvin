"""
Per-send context variables available in each email template type.

These are {{lower_case}} slugs injected at send time — distinct from
{{UPPER_CASE}} workspace variables which are static.
"""

from typing import TypedDict


class TemplateVar(TypedDict):
    slug: str
    description: str
    example: str


# Variables available in every email template
COMMON_VARS: list[TemplateVar] = [
    {"slug": "workspace_name", "description": "Name of the workspace", "example": "Acme Blog"},
]

# Variables available per template type
TEMPLATE_VARS: dict[str, list[TemplateVar]] = {
    "invitation": [
        {"slug": "inviter_name", "description": "Name of the person who sent the invite", "example": "Jane Smith"},
        {"slug": "invitation_url", "description": "Link the recipient clicks to accept", "example": "https://..."},
        {"slug": "workspace_name", "description": "Name of the workspace being joined", "example": "Acme Blog"},
    ],
    "password_reset": [
        {"slug": "username", "description": "Recipient's username", "example": "jsmith"},
        {"slug": "reset_url", "description": "Password reset link", "example": "https://..."},
        {"slug": "expiry_hours", "description": "Hours until the link expires", "example": "24"},
    ],
    "welcome": [
        {"slug": "username", "description": "New user's username", "example": "jsmith"},
        {"slug": "first_name", "description": "User's first name", "example": "Jane"},
        {"slug": "login_url", "description": "Link to log in", "example": "https://..."},
    ],
    "notification": [
        {"slug": "title", "description": "Notification title", "example": "New comment on your post"},
        {"slug": "message", "description": "Notification body text", "example": "Someone replied to..."},
        {"slug": "action_url", "description": "Link to the relevant content", "example": "https://..."},
    ],
}


def get_vars_for_type(template_type: str | None) -> list[TemplateVar]:
    """Return per-send variables for a given template type."""
    if template_type and template_type in TEMPLATE_VARS:
        return TEMPLATE_VARS[template_type]
    return COMMON_VARS
