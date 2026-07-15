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
    variables: dict = {}


@controller(router)
class PlatformEmailController(BaseUserController):

    @router.post("/test", response_model=EmailSuccess)
    def send_test_email(
        self,
        data: EmailTest,
        accept_language: str | None = Header(default=None),
    ) -> EmailSuccess:
        """Send a test email. Uses provided subject/message if given, otherwise generic defaults."""
        from marvin.services.email.email_service import EmailTemplate

        email_service = EmailService(locale=accept_language)
        try:
            if data.subject or data.message:
                from marvin.services.secrets.resolver import resolve
                subject = resolve(data.subject or "Test Email", self.group_id, allow_secrets=False)
                message = resolve(data.message or "This is a test email.", self.group_id, allow_secrets=False)
                template = EmailTemplate(
                    subject=subject,
                    header_text=subject,
                    message_top=message,
                    button_link=str(self.settings.BASE_URL),
                    button_text="Open Marvin",
                )
                success = email_service.send_email(data.email, template)
            else:
                success = email_service.send_test_email(data.email)
            if not success:
                return EmailSuccess(success=False, error="Email service returned failure without exception.")
        except Exception as e:
            self.logger.error(f"Test email failed: {e}")
            return EmailSuccess(success=False, error=str(e))
        return EmailSuccess(success=True)

    @router.get("/template-vars")
    def list_template_vars(self, template_type: str | None = None) -> dict:
        """Return available per-send variables and required vars for a template type."""
        from marvin.services.email.template_variables import get_vars_for_type, TEMPLATE_VARS
        from marvin.services.email.system_templates import get_required_vars
        return {
            "context_vars": get_vars_for_type(template_type),
            "required_vars": get_required_vars(template_type or ""),
            "available_types": list(TEMPLATE_VARS.keys()),
        }

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
                **data.variables,  # User-provided vars override defaults
            }

            warning = None
            try:
                email_service = EmailService()
                success = email_service._send_db_template(data.recipient_email, template, test_variables)
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to send test email. Check SMTP configuration.",
                    )
            except ValueError as e:
                # Required vars missing from template content — warn but still attempt send
                # by bypassing validation for test sends
                warning = str(e)
                self.logger.warning(f"Test send bypassing validation: {e}")
                try:
                    email_service = EmailService()
                    from marvin.services.email.email_service import EmailTemplate
                    from marvin.services.secrets.resolver import resolve
                    group_id = template.group_id
                    def _r(text):
                        return resolve(text or "", group_id, allow_secrets=False, context=test_variables)
                    from jinja2 import Template as JinjaTemplate
                    tpl = EmailTemplate(
                        subject=JinjaTemplate(_r(template.subject)).render(**test_variables),
                        header_text=JinjaTemplate(_r(template.header_text)).render(**test_variables),
                        message_top=JinjaTemplate(_r(template.message_top)).render(**test_variables),
                        message_bottom=JinjaTemplate(_r(template.message_bottom or "")).render(**test_variables),
                        button_link=test_variables.get("button_link", ""),
                        button_text=JinjaTemplate(_r(template.button_text or "")).render(**test_variables),
                        workspace_name=test_variables.get("workspace_name", ""),
                    )
                    email_service.send_email(data.recipient_email, tpl)
                except Exception as inner:
                    self.logger.error(f"Template test fallback send failed: {inner}")
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(inner))
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Template test email failed: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        result = {"message": f"Test email sent to {data.recipient_email}"}
        if warning:
            result["warning"] = f"Some required variables were missing from the template: {warning}"
        return result
