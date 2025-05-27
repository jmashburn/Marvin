"""
This module defines Pydantic schemas related to administrative email functionalities
within the Marvin application.

These schemas are used for request and response models in endpoints that
check email configuration status or send test emails.
"""

from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model for Marvin schemas


class EmailReady(_MarvinModel):
    """
    Schema indicating the readiness of the email (SMTP) service.
    """

    ready: bool  # True if the email service is configured and enabled, False otherwise.


class EmailSuccess(_MarvinModel):
    """
    Schema for the response when an email operation (like sending a test email) is attempted.
    Indicates success or failure and provides an error message if applicable.
    """

    success: bool  # True if the email operation was successful, False otherwise.
    error: str | None = None  # An optional error message if the operation failed.


class EmailTest(_MarvinModel):
    """
    Schema for the request body when sending a test email.
    Specifies the recipient email address.
    """

    email: str  # The email address to which the test email should be sent.
