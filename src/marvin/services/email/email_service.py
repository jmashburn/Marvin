"""
This module provides services for constructing and sending emails within the
Marvin application.

It defines an `EmailTemplate` Pydantic model to structure email content and an
`EmailService` class responsible for rendering these templates into HTML and
dispatching emails using a configurable email sender (defaulting to SMTP).
The service supports sending various types of emails, such as password resets,
invitations, and test emails.
"""

from pathlib import Path  # For path manipulation (template directory)

from jinja2 import Template  # For rendering HTML templates
from pydantic import BaseModel  # For creating data models like EmailTemplate

from marvin.core.root_logger import get_logger  # Application logger
from marvin.services import BaseService  # Base service class

# Email sender implementations
from .email_senders import ABCEmailSender, DefaultEmailSender

# Current working directory of this file, used to locate the 'templates' subdirectory.
CWD = Path(__file__).parent

# Logger instance for this module
logger = get_logger()


class EmailTemplate(BaseModel):
    """
    Pydantic model representing the content structure for an email template.

    This model holds various parts of an email, such as subject, header,
    messages, and call-to-action button details. The content for these fields
    is often provided as localization keys (e.g., "emails.password.subject")
    which would be resolved by a translation service if integrated.
    """

    subject: str
    header_text: str
    message_top: str
    message_bottom: str = ""
    button_link: str = ""
    button_text: str = ""
    workspace_name: str = ""

    def render_html(self, template_file: Path) -> str:  # Renamed `template` to `template_file`
        """
        Renders the email content into an HTML string using a Jinja2 template.

        The method reads the template content from the provided `template_file` path
        and renders it by passing the current `EmailTemplate` instance's data
        (converted to a dictionary) to the template.

        Args:
            template_file (Path): The path to the Jinja2 HTML template file.

        Returns:
            str: The rendered HTML content as a string.
        """
        # Read the template file content
        tmpl_str = template_file.read_text(encoding="utf-8")  # Added encoding
        jinja_template = Template(tmpl_str)  # Create a Jinja2 Template object

        # Render the template with the data from this EmailTemplate instance
        # The template should expect a 'data' variable containing the model's fields.
        return jinja_template.render(data=self.model_dump())


class EmailService(BaseService):
    """
    Service class for sending emails.

    This service handles the construction of email content using `EmailTemplate`
    and dispatches emails through a configured email sender (which defaults to
    `DefaultEmailSender` if not provided). It provides methods for sending
    specific types of application emails like password resets and invitations.
    """

    def __init__(self, sender: ABCEmailSender | None = None, locale: str | None = None) -> None:
        """
        Initializes the EmailService.

        Args:
            sender (ABCEmailSender | None, optional): An email sender instance.
                If None, `DefaultEmailSender` is used. Defaults to None.
            locale (str | None, optional): The locale string (e.g., "en_US") for
                email localization. Currently, the translator part is commented out,
                so this parameter's effect is pending full i18n implementation.
                Defaults to None.
        """
        self.templates_dir: Path = CWD / "templates"  # Path to the email templates directory
        self.default_template: Path = self.templates_dir / "default.html"  # Path to the default email template

        if Path(self.templates_dir / self.settings._DEFAULT_EMAIL_TEMPLATE).is_file():
            self.default_template: Path = (
                self.templates_dir / self.settings._DEFAULT_EMAIL_TEMPLATE
            )  # Path to the default email template per settings

        if Path(self.directories.TEMPLATE_DIR / self.settings._DEFAULT_EMAIL_TEMPLATE).is_file():
            self.templates_dir = self.directories.TEMPLATE_DIR
            self.default_template = self.templates_dir / self.settings._DEFAULT_EMAIL_TEMPLATE

        self.logger.debug(f"Loading {self.templates_dir} in {self.default_template}")

        # Use provided sender or instantiate DefaultEmailSender
        self.sender: ABCEmailSender = sender or DefaultEmailSender()

        # Placeholder for localization/translation functionality.
        # If uncommented, `local_provider` would need to be defined and return a Translator instance.
        # self.translator: Translator = local_provider(locale)
        # For now, string keys in EmailTemplate will be used as-is if no translation occurs.
        self.logger.info(f"EmailService initialized. Sender: {type(self.sender).__name__}. Locale: {locale or 'default'}.")

    def send_email(self, email_to: str, email_data: EmailTemplate) -> bool:  # Renamed `data` to `email_data`
        """
        Sends an email using the configured sender and default HTML template.

        This is a generic method used by more specific email sending methods.
        It checks if SMTP is enabled in settings before attempting to send.

        Args:
            email_to (str): The recipient's email address.
            email_data (EmailTemplate): An `EmailTemplate` instance containing the
                                        content for the email.

        Returns:
            bool: True if the email was sent successfully (or if SMTP is disabled),
                  False otherwise. Note: Returning True when SMTP is disabled might
                  be misleading; consider alternative return or logging.
        """
        if not self.settings.SMTP_ENABLED:
            self.logger.info(f"SMTP is disabled. Email not sent to {email_to} (Subject: {email_data.subject}).")
            # Returning False might be more indicative that no email was actually sent.
            # However, if the intent is "operation considered successful if SMTP off", True is okay.
            # Let's change to False for clarity that no email dispatch occurred.
            return False

        # Render the HTML content using the default template and email_data
        html_content = email_data.render_html(self.default_template)

        # Send the email via the configured sender
        success = self.sender.send(email_to, email_data.subject, html_content)
        if success:
            self.logger.info(f"Email '{email_data.subject}' sent successfully to {email_to}.")
        else:
            self.logger.error(f"Failed to send email '{email_data.subject}' to {email_to}.")
        return success

    def send_forgot_password(
        self,
        recipient_address: str,
        reset_password_url: str,
        username: str = "",
        group_id: str | None = None,
    ) -> bool:
        """Sends a password reset email, using a DB template if available."""
        db_template = self._get_db_template("password_reset", group_id)
        if db_template:
            return self._send_db_template(
                recipient_address,
                db_template,
                {
                    "reset_url": reset_password_url,
                    "button_link": reset_password_url,
                    "username": username,
                    "expiry_hours": "24",
                },
            )
        forgot_password_template = EmailTemplate(
            subject="Reset your password",
            header_text="Password Reset Request",
            message_top=f"We received a request to reset the password for {username or 'your account'}.",
            message_bottom="If you didn't request this, you can safely ignore this email.",
            button_link=reset_password_url,
            button_text="Reset Password",
        )
        return self.send_email(recipient_address, forgot_password_template)

    def send_invitation(
        self,
        recipient_address: str,
        invitation_url: str,
        group_id: str | None = None,
        workspace_name: str = "",
        inviter_name: str = "",
    ) -> bool:
        """
        Sends a group invitation email to a prospective user.

        The email contains a unique URL for accepting the invitation and registering.
        Looks for a database template first, falls back to filesystem/hardcoded template.

        Args:
            recipient_address (str): The email address of the person being invited.
            invitation_url (str): The URL the recipient will click to accept the invitation.
            group_id (str | None): Workspace ID for workspace-specific templates.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        # Try to load template from database
        db_template = self._get_db_template("invitation", group_id)

        if db_template:
            return self._send_db_template(
                recipient_address,
                db_template,
                {
                    "invitation_url": invitation_url,
                    "button_link": invitation_url,
                    "workspace_name": workspace_name,
                    "inviter_name": inviter_name,
                },
            )

        # Fallback to hardcoded template
        invitation_template = EmailTemplate(
            subject="Invitation to Join",
            header_text="You're Invited!",
            message_top="You have been invited to join",
            message_bottom="Please click the button above to accept the invitation.",
            button_link=invitation_url,
            button_text="Accept Invitation",
        )
        return self.send_email(recipient_address, invitation_template)

    def send_test_email(self, recipient_address: str) -> bool:  # Renamed param
        """
        Sends a test email to verify SMTP configuration.

        The email uses generic test content and links to the application's base URL.
        Content is defined by localization keys.

        Args:
            recipient_address (str): The email address to send the test email to.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        # Construct the EmailTemplate with content specific for a test email
        test_email_template = EmailTemplate(
            subject="Test Email",  # Localization key for subject
            header_text="Test Email",
            message_top="This is a test email",
            message_bottom="Please click the button above to test the email.",
            button_link=str(self.settings.BASE_URL),  # Link to the application's base URL
            button_text="Open",
        )
        return self.send_email(recipient_address, test_email_template)

    def _get_db_template(self, template_type: str, group_id: str | None = None):
        """Get email template from database.

        Looks for workspace-specific template first, then system-wide template.

        Args:
            template_type: Type of template (invitation, password_reset, etc.)
            group_id: Workspace ID for workspace-specific templates

        Returns:
            EmailTemplateModel or None if not found
        """
        try:
            from marvin.db.db_setup import session_context
            from marvin.db.models.groups.email_templates import EmailTemplateModel

            with session_context() as session:
                # Try workspace-specific template first
                if group_id:
                    template = session.query(EmailTemplateModel).filter_by(template_type=template_type, group_id=group_id, enabled=True).first()
                    if template:
                        return template

                # Fall back to system-wide template
                template = session.query(EmailTemplateModel).filter_by(template_type=template_type, group_id=None, enabled=True).first()
                return template
        except Exception as e:
            self.logger.warning(f"Failed to load database template '{template_type}': {e}")
            return None

    def _send_db_template(self, recipient_address: str, db_template, variables: dict) -> bool:
        """Send email using database template.

        Supports two modes:
        1. Structured: Uses header_text, message_top, etc. with default.html template
        2. Custom HTML: Uses custom_html field with Jinja2 rendering

        {{SLUG}} workspace secrets/variables are resolved before Jinja2 rendering.

        Args:
            recipient_address: Email recipient
            db_template: EmailTemplateModel from database
            variables: Dictionary of variables to render in the template

        Returns:
            bool: True if email sent successfully
        """
        # Validate required variables BEFORE the rendering try-block so ValueError propagates
        from marvin.services.email.system_templates import validate_template_content
        # Only validate structured-field required vars when not using custom HTML or markdown-rendered HTML
        has_custom_html = bool(db_template.custom_html and db_template.custom_html.strip())
        if not has_custom_html:
            content_fields = {
                "subject": db_template.subject or "",
                "header_text": db_template.header_text or "",
                "message_top": db_template.message_top or "",
                "message_bottom": db_template.message_bottom or "",
            }
            missing = validate_template_content(db_template.template_type or "", content_fields)
            if missing:
                raise ValueError(f"Template is missing required variables: {', '.join('{{' + v + '}}' for v in missing)}")

        try:
            from jinja2 import Template
            from marvin.services.secrets.resolver import resolve

            group_id = getattr(db_template, "group_id", None)

            def _r(text: str | None) -> str:
                return resolve(text or "", group_id, allow_secrets=False, context=variables)

            # Render subject with Jinja2
            subject_template = Template(_r(db_template.subject))
            subject = subject_template.render(**variables)

            # Determine rendering mode
            raw_custom = db_template.custom_html or ""
            if raw_custom.strip():
                # Log any {{ slug }} in the template that aren't in variables
                import re as _re
                used_slugs = set(_re.findall(r'\{\{\s*([a-z_][a-z0-9_]*)\s*\}\}', raw_custom))
                unresolved = [s for s in used_slugs if s not in variables]
                if unresolved:
                    self.logger.warning(
                        f"EmailEventListener: unresolved variables in template '{db_template.name}': "
                        + ", ".join(f"{{{{{s}}}}}" for s in sorted(unresolved))
                    )
                # Render content through Jinja2 for variable substitution
                body_html = Template(_r(raw_custom)).render(**variables)
                # Wrap in default.html so the email has proper structure/styling
                template_data = EmailTemplate(
                    subject=subject,
                    header_text=Template(_r(db_template.header_text or "")).render(**variables) or variables.get("message_title", ""),
                    message_top=body_html,
                    message_bottom=Template(_r(db_template.message_bottom or "")).render(**variables),
                    button_link=(
                        variables.get("invitation_url") or variables.get("reset_url")
                        or variables.get("login_url") or variables.get("action_url")
                        or variables.get("button_link", "")
                    ),
                    button_text=Template(_r(db_template.button_text or "")).render(**variables),
                    workspace_name=variables.get("workspace_name", ""),
                )
                html_content = template_data.render_html(self.default_template)
            else:
                # Mode 2: Structured - resolve slugs in each field then Jinja2
                template_data = EmailTemplate(
                    subject=subject,
                    header_text=Template(_r(db_template.header_text)).render(**variables),
                    message_top=Template(_r(db_template.message_top)).render(**variables),
                    message_bottom=Template(_r(db_template.message_bottom)).render(**variables),
                    # Derive button_link from type-specific URL variables if present
                    button_link=(
                        variables.get("invitation_url")
                        or variables.get("reset_url")
                        or variables.get("login_url")
                        or variables.get("action_url")
                        or variables.get("button_link", "")
                    ),
                    button_text=Template(_r(db_template.button_text)).render(**variables),
                    workspace_name=variables.get("workspace_name", ""),
                )
                # Render with default.html template
                html_content = template_data.render_html(self.default_template)

            # Send via configured sender
            if not self.settings.SMTP_ENABLED:
                self.logger.info(f"SMTP is disabled. Email not sent to {recipient_address} (Subject: {subject}).")
                return False

            success = self.sender.send(recipient_address, subject, html_content)
            if success:
                self.logger.info(f"Email '{subject}' sent successfully to {recipient_address} (DB template: {db_template.name}).")
            else:
                self.logger.error(f"Failed to send email '{subject}' to {recipient_address}.")
            return success
        except Exception as e:
            self.logger.error(f"Error rendering database template: {e}")
            return False
