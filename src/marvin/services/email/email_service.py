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
    """The subject line of the email (can be a localization key)."""
    header_text: str
    """Text for the header section of the email (can be a localization key)."""
    message_top: str
    """The primary message content, appearing at the top (can be a localization key)."""
    message_bottom: str
    """Additional message content, appearing at the bottom (can be a localization key)."""
    button_link: str
    """The URL for the call-to-action button in the email."""
    button_text: str
    """The text displayed on the call-to-action button (can be a localization key)."""

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

    def send_forgot_password(self, recipient_address: str, reset_password_url: str) -> bool:  # Renamed params
        """
        Sends a "forgot password" email to the user.

        The email contains a unique URL for resetting their password.
        Content is defined by localization keys (e.g., "emails.password.subject").

        Args:
            recipient_address (str): The email address of the user who forgot their password.
            reset_password_url (str): The URL the user will click to reset their password.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        # Construct the EmailTemplate with content specific to password reset
        # These string values are presumably localization keys.
        forgot_password_template = EmailTemplate(
            subject="Forgot Password",  # Localization key for subject
            header_text="Forgot Password",
            message_top="You have requested to reset your password.",
            message_bottom="Please click the button above to reset your password.",
            button_link=reset_password_url,  # The actual reset URL
            button_text="Reset Password",
        )
        return self.send_email(recipient_address, forgot_password_template)

    def send_invitation(self, recipient_address: str, invitation_url: str) -> bool:  # Renamed params
        """
        Sends a group invitation email to a prospective user.

        The email contains a unique URL for accepting the invitation and registering.
        Content is defined by localization keys.

        Args:
            recipient_address (str): The email address of the person being invited.
            invitation_url (str): The URL the recipient will click to accept the invitation.

        Returns:
            bool: True if the email was sent successfully, False otherwise.
        """
        # Construct the EmailTemplate with content specific to invitations
        invitation_template = EmailTemplate(
            subject="Invitation to Join",  # Localization key for subject
            header_text="You're Invited!",
            message_top="You have been invited to join",
            message_bottom="Please click the button above to accept the invitation.",
            button_link=invitation_url,  # The actual invitation URL
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
