"""
Platform email endpoint — workspace-scoped test email.

Lets any authenticated workspace user send a test email to verify
SMTP is working. Uses the same EmailService as the admin endpoint
but is accessible without admin privileges.
"""

from fastapi import APIRouter, Header
from pydantic import EmailStr

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.admin.email import EmailSuccess, EmailTest
from marvin.services.email.email_service import EmailService

router = APIRouter(prefix="/email")


@controller(router)
class PlatformEmailController(BaseUserController):

    @router.post("/test", response_model=EmailSuccess)
    def send_test_email(
        self,
        data: EmailTest,
        accept_language: str | None = Header(default=None),
    ) -> EmailSuccess:
        """Send a test email to verify SMTP configuration. Available to all workspace users."""
        email_service = EmailService(locale=accept_language)
        try:
            success = email_service.send_test_email(data.email)
            if not success:
                return EmailSuccess(success=False, error="Email service returned failure without exception.")
        except Exception as e:
            self.logger.error(f"Test email failed: {e}")
            return EmailSuccess(success=False, error=str(e))
        return EmailSuccess(success=True)
