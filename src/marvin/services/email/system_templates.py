"""
System email template definitions and seeder.

System templates (group_id=NULL) are the defaults for all system emails.
Workspace owners can "Customize" them to create workspace-specific overrides.

Each definition includes:
  - required_vars: {{lower_case}} slugs that MUST be present for the email to work
  - optional_vars: nice to have but not critical
  - default content with the variables shown in context
"""

from dataclasses import dataclass, field

from marvin.core.root_logger import get_logger

logger = get_logger(__name__)


@dataclass
class SystemTemplateDefinition:
    template_type: str
    name: str
    description: str
    subject: str
    header_text: str
    message_top: str
    message_bottom: str
    button_text: str
    button_placeholder: str  # shown in UI as the expected button_link variable
    required_vars: list[str]
    optional_vars: list[str] = field(default_factory=list)


SYSTEM_TEMPLATES: list[SystemTemplateDefinition] = [
    SystemTemplateDefinition(
        template_type="invitation",
        name="Workspace Invitation",
        description="Sent when a user is invited to join a workspace.",
        subject="You've been invited to join {{workspace_name}}",
        header_text="You're Invited!",
        message_top=(
            "{{inviter_name}} has invited you to join {{workspace_name}}.\n\n"
            "Click the button below to accept the invitation and get started."
        ),
        message_bottom=(
            "If you weren't expecting this invitation, you can safely ignore this email. "
            "The link will expire in 7 days."
        ),
        button_text="Accept Invitation",
        button_placeholder="{{invitation_url}}",
        required_vars=["invitation_url", "workspace_name"],
        optional_vars=["inviter_name"],
    ),
    SystemTemplateDefinition(
        template_type="password_reset",
        name="Password Reset",
        description="Sent when a user requests a password reset.",
        subject="Reset your Marvin password",
        header_text="Password Reset Request",
        message_top=(
            "We received a request to reset the password for your account ({{username}}).\n\n"
            "Click the button below to choose a new password. This link expires in {{expiry_hours}} hours."
        ),
        message_bottom=(
            "If you didn't request a password reset, you can safely ignore this email. "
            "Your password will not be changed."
        ),
        button_text="Reset Password",
        button_placeholder="{{reset_url}}",
        required_vars=["reset_url"],
        optional_vars=["username", "expiry_hours"],
    ),
    SystemTemplateDefinition(
        template_type="welcome",
        name="Welcome",
        description="Sent when a new user joins a workspace.",
        subject="Welcome to {{workspace_name}}!",
        header_text="Welcome, {{first_name}}!",
        message_top=(
            "Your account has been created. You're now a member of {{workspace_name}}.\n\n"
            "Click below to log in and get started."
        ),
        message_bottom="Need help? Reach out to your workspace administrator.",
        button_text="Log In",
        button_placeholder="{{login_url}}",
        required_vars=["login_url"],
        optional_vars=["first_name", "username", "workspace_name"],
    ),
    SystemTemplateDefinition(
        template_type="notification",
        name="General Notification",
        description="General-purpose notification email.",
        subject="{{title}}",
        header_text="{{title}}",
        message_top="{{message}}",
        message_bottom="",
        button_text="View",
        button_placeholder="{{action_url}}",
        required_vars=["title", "message"],
        optional_vars=["action_url"],
    ),
]

# Quick lookup by type
TEMPLATE_BY_TYPE: dict[str, SystemTemplateDefinition] = {
    t.template_type: t for t in SYSTEM_TEMPLATES
}


def get_required_vars(template_type: str) -> list[str]:
    """Return required variable slugs for a template type."""
    defn = TEMPLATE_BY_TYPE.get(template_type)
    return defn.required_vars if defn else []


def validate_template_content(template_type: str, content_fields: dict[str, str]) -> list[str]:
    """
    Check that all required {{variable}} slugs appear somewhere in the template content.

    Returns a list of missing required variable slugs (empty = all present).
    """
    required = get_required_vars(template_type)
    if not required:
        return []

    all_content = " ".join(v for v in content_fields.values() if v)
    missing = [slug for slug in required if "{{" + slug + "}}" not in all_content]
    return missing


def seed_system_templates(session) -> int:
    """
    Create system templates (group_id=NULL) if they don't already exist.
    Idempotent — skips existing template types. Returns count of created templates.
    """
    from marvin.db.models.groups.email_templates import EmailTemplateModel
    from sqlalchemy import select

    created = 0
    for defn in SYSTEM_TEMPLATES:
        existing = session.execute(
            select(EmailTemplateModel).where(
                EmailTemplateModel.template_type == defn.template_type,
                EmailTemplateModel.group_id.is_(None),
            )
        ).scalar_one_or_none()

        if existing:
            continue

        template = EmailTemplateModel()
        template.template_type = defn.template_type
        template.name = defn.name
        template.description = defn.description
        template.subject = defn.subject
        template.header_text = defn.header_text
        template.message_top = defn.message_top
        template.message_bottom = defn.message_bottom
        template.button_text = defn.button_text
        template.group_id = None
        template.enabled = True
        session.add(template)
        created += 1
        logger.info(f"Seeded system email template: {defn.template_type}")

    if created:
        session.commit()
        logger.info(f"Email template seeder: created {created} system template(s)")

    return created
