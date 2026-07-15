"""
Platform email endpoints — workspace-scoped email operations.
"""

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import UUID4, BaseModel, EmailStr

from marvin.routes._base import BaseUserController, controller
from marvin.schemas.admin.email import EmailSuccess, EmailTest
from marvin.services.email.email_service import EmailService

router = APIRouter(prefix="/email")


class TemplateTestRequest(BaseModel):
    recipient_email: EmailStr


@controller(router)
class PlatformEmailController(BaseUserController):

    @router.post("/test", response_model=EmailSuccess)
    def send_test_email(
        self,
        data: EmailTest,
        accept_language: str | None = Header(default=None),
    ) -> EmailSuccess:
        """Send a test email to verify SMTP configuration."""
        email_service = EmailService(locale=accept_language)
        try:
            success = email_service.send_test_email(data.email)
            if not success:
                return EmailSuccess(success=False, error="Email service returned failure without exception.")
        except Exception as e:
            self.logger.error(f"Test email failed: {e}")
            return EmailSuccess(success=False, error=str(e))
        return EmailSuccess(success=True)

    @router.post("/templates/{template_id}/test")
    def send_template_test_email(self, template_id: UUID4, data: TemplateTestRequest) -> dict:
        """Send a test email using a specific workspace template with its subject and body."""
        from marvin.db.db_setup import session_context
        from marvin.db.models.groups.email_templates import EmailTemplateModel
        from sqlalchemy import select, and_

        with session_context() as session:
            template = session.execute(
                select(EmailTemplateModel).where(
                    and_(
                        EmailTemplateModel.id == template_id,
                        EmailTemplateModel.group_id == self.group_id,
                    )
                )
            ).scalar_one_or_none()

            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Email template not found.",
                )

            test_variables = {
                "workspace_name": self.group.name if hasattr(self, "group") else "Your Workspace",
                "button_link": str(self.settings.BASE_URL),
                "invitation_url": str(self.settings.BASE_URL),
            }

            try:
                email_service = EmailService()
                success = email_service._send_db_template(data.recipient_email, template, test_variables)
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to send test email. Check SMTP configuration.",
                    )
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Template test email failed: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        return {"message": f"Test email sent to {data.recipient_email}"}
