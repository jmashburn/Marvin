"""
This module defines the FastAPI controller for administrative email functionalities
within the Marvin application.

It provides endpoints for administrators to check the email (SMTP) configuration
status and to send a test email to verify if the setup is working correctly.
"""

from typing import Annotated  # For type hinting with FastAPI Header

from fastapi import APIRouter, Header  # FastAPI components for routing and header parameters

# Marvin base controller and schema imports
from marvin.routes._base import BaseAdminController, controller  # Base controller for admin routes
from marvin.schemas.admin.email import (
    EmailReady,
    EmailSuccess,
    EmailTest,
)  # Pydantic schemas for email responses/requests
from marvin.services.email import EmailService  # Service for handling email operations

# APIRouter for admin "email" section, prefixed with /email
# All routes in this controller will be under /admin/email.
router = APIRouter(prefix="/email")


@controller(router)
class AdminEmailController(BaseAdminController):
    """
    Controller for administrative email operations.

    Provides endpoints to check SMTP configuration status and send test emails.
    Requires administrator privileges for all operations.
    """

    @router.get("", response_model=EmailReady, summary="Check Email Configuration Status")
    async def check_email_config(self) -> EmailReady:
        """
        Checks and returns the status of the SMTP email configuration.

        Indicates whether the SMTP settings are enabled in the application configuration,
        which is a prerequisite for sending emails. Accessible only by administrators.

        Returns:
            EmailReady: A Pydantic model indicating if the email (SMTP) service is ready.
        """
        # Returns a simple boolean status based on application settings
        return EmailReady(ready=self.settings.SMTP_ENABLED)

    @router.post("", response_model=EmailSuccess, summary="Send a Test Email")
    async def send_test_email(
        self,
        data: EmailTest,  # Pydantic model containing the recipient email address
        accept_language: Annotated[str | None, Header()] = None,  # Optional language preference from header
    ) -> EmailSuccess:
        """
        Sends a test email to the email address specified in the request body.

        This endpoint is used to verify that the SMTP email service is correctly
        configured and operational. The email content might be localized based
        on the `accept_language` header. Accessible only by administrators.

        Args:
            data (EmailTest): Request body containing the `email` field for the recipient.
            accept_language (str | None, optional): The preferred language for the
                email content, extracted from the 'Accept-Language' header.
                Defaults to None (system default language).

        Returns:
            EmailSuccess: A Pydantic model indicating whether the email was sent
                          successfully and any error message if it failed.
        """
        # Initialize the email service, potentially with locale for localized templates
        email_service = EmailService(locale=accept_language)
        email_sent_successfully = False  # Default status
        error_message: str | None = None  # Default error message

        try:
            # Attempt to send the test email using the email service
            email_sent_successfully = email_service.send_test_email(data.email)
            if not email_sent_successfully:  # If service returns False without exception
                error_message = "Email service reported failure without raising an exception."
        except Exception as e:
            # Log the exception and capture the error message
            self.logger.error(f"Failed to send test email to {data.email}: {e}")
            error_message = str(e)

        return EmailSuccess(success=email_sent_successfully, error=error_message)
