"""Email template management controller for workspace-scoped email templates."""

from functools import cached_property

from fastapi import APIRouter, HTTPException, status
from pydantic import UUID4

from marvin.routes._base import MarvinCrudRoute
from marvin.routes._base.base_controllers import BaseUserController
from marvin.routes._base.controller import controller
from marvin.schemas.group.email_template import (
    EmailTemplateCreate,
    EmailTemplateRead,
    EmailTemplateSummary,
    EmailTemplateUpdate,
)
from pydantic import BaseModel, EmailStr
from marvin.services.event_bus_service.event_types import EventOperation, EventTypes

router = APIRouter(prefix="/platform/workspaces/{group_id}/email-templates", route_class=MarvinCrudRoute)


class TestEmailRequest(BaseModel):
    """Request to send a test email."""

    recipient_email: EmailStr


@controller(router)
class EmailTemplateController(BaseUserController):
    """
    Controller for managing workspace email templates.

    Provides CRUD operations for email templates that can customize
    invitation, password reset, and notification emails per workspace.
    """

    @cached_property
    def repo(self):
        """Repository for email templates."""
        if not self.user:
            raise Exception("No user logged in")
        from marvin.repos.repository_generic import RepositoryGeneric
        from marvin.db.models.groups.email_templates import EmailTemplateModel
        from marvin.schemas.group.email_template import EmailTemplateRead

        return RepositoryGeneric(
            self.repos.session,
            primary_key="id",
            sql_model=EmailTemplateModel,
            schema=EmailTemplateRead,
        )

    @router.get("", response_model=list[EmailTemplateSummary], summary="List Email Templates")
    def list_templates(self, group_id: UUID4) -> list[EmailTemplateSummary]:
        """
        List all email templates for the workspace.

        Returns both workspace-specific and system-wide templates.

        Args:
            group_id: Workspace ID

        Returns:
            List of email template summaries
        """
        self._check_workspace_access(group_id)

        from marvin.db.models.groups.email_templates import EmailTemplateModel
        from sqlalchemy import or_

        # Query workspace templates + system templates in one query
        templates = (
            self.repos.session.query(EmailTemplateModel)
            .filter(or_(EmailTemplateModel.group_id == group_id, EmailTemplateModel.group_id.is_(None)))
            .all()
        )

        return [EmailTemplateSummary.model_validate(t) for t in templates]

    @router.get("/{template_id}", response_model=EmailTemplateRead, summary="Get Email Template")
    def get_template(self, group_id: UUID4, template_id: UUID4) -> EmailTemplateRead:
        """
        Get a specific email template by ID.

        Args:
            group_id: Workspace ID
            template_id: Template ID

        Returns:
            Email template details
        """
        self._check_workspace_access(group_id)

        template = self.repo.get_one(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email template not found: {template_id}",
            )

        return EmailTemplateRead.model_validate(template)

    @router.post("", response_model=EmailTemplateRead, status_code=status.HTTP_201_CREATED, summary="Create Email Template")
    def create_template(self, group_id: UUID4, data: EmailTemplateCreate) -> EmailTemplateRead:
        """
        Create a new email template for the workspace.

        Args:
            group_id: Workspace ID
            data: Template data

        Returns:
            Created email template
        """
        self._check_admin_access(group_id)

        # Ensure group_id matches
        if data.group_id and str(data.group_id) != str(group_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template group_id must match workspace group_id",
            )

        # Set group_id from path
        create_data = data.model_dump()
        create_data["group_id"] = str(group_id)

        # Create template using SQLAlchemy directly
        from marvin.db.models.groups.email_templates import EmailTemplateModel

        template = EmailTemplateModel(**create_data)
        self.repos.session.add(template)
        self.repos.session.commit()
        self.repos.session.refresh(template)

        # Dispatch event
        self.event_bus.dispatch(
            integration_id="email_template_management",
            group_id=group_id,
            event_type=EventTypes.email_template_created,
            document_data={
                "operation": EventOperation.create,
                "template_id": str(template.id),
                "template_type": template.template_type,
                "workspace_id": group_id,
            },
            message=f"Email template created: {template.name} ({template.template_type})",
            user_id=self.user.id if self.user else None,
        )

        return EmailTemplateRead.model_validate(template)

    @router.patch("/{template_id}", response_model=EmailTemplateRead, summary="Update Email Template")
    def update_template(self, group_id: UUID4, template_id: UUID4, data: EmailTemplateUpdate) -> EmailTemplateRead:
        """
        Update an email template.

        Args:
            group_id: Workspace ID
            template_id: Template ID
            data: Updated template data

        Returns:
            Updated email template
        """
        self._check_admin_access(group_id)

        # Verify template exists and belongs to this workspace
        template = self.repo.get_one(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email template not found: {template_id}",
            )

        # Don't allow updating system templates from workspace controller
        if template.group_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update system-wide templates from workspace controller",
            )

        update_data = data.model_dump(exclude_unset=True)
        updated_template = self.repo.update(template_id, update_data)

        # Dispatch event
        self.event_bus.dispatch(
            integration_id="email_template_management",
            group_id=group_id,
            event_type=EventTypes.email_template_updated,
            document_data={
                "operation": EventOperation.update,
                "template_id": str(template_id),
                "template_type": updated_template.template_type,
                "workspace_id": group_id,
            },
            message=f"Email template updated: {updated_template.name}",
            user_id=self.user.id if self.user else None,
        )

        return EmailTemplateRead.model_validate(updated_template)

    @router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Email Template")
    def delete_template(self, group_id: UUID4, template_id: UUID4) -> None:
        """
        Delete an email template.

        Args:
            group_id: Workspace ID
            template_id: Template ID
        """
        self._check_admin_access(group_id)

        # Verify template exists and belongs to this workspace
        template = self.repo.get_one(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email template not found: {template_id}",
            )

        # Don't allow deleting system templates from workspace controller
        if template.group_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system-wide templates from workspace controller",
            )

        template_name = template.name
        template_type = template.template_type

        self.repo.delete(template_id)

        # Dispatch event
        self.event_bus.dispatch(
            integration_id="email_template_management",
            group_id=group_id,
            event_type=EventTypes.email_template_deleted,
            document_data={
                "operation": EventOperation.delete,
                "template_id": str(template_id),
                "template_type": template_type,
                "workspace_id": group_id,
            },
            message=f"Email template deleted: {template_name}",
            user_id=self.user.id if self.user else None,
        )

    @router.post("/{template_id}/test", status_code=status.HTTP_200_OK, summary="Send Test Email")
    def send_test_email(self, group_id: UUID4, template_id: UUID4, data: TestEmailRequest) -> dict:
        """
        Send a test email using the specified template.

        Args:
            group_id: Workspace ID
            template_id: Template ID
            data: Test email request with recipient address

        Returns:
            Success message
        """
        self._check_workspace_access(group_id)

        # Get the template
        template = self.repo.get_one(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Email template not found: {template_id}",
            )

        # Send test email
        from marvin.services.email.email_service import EmailService

        email_service = EmailService()

        # Build test variables
        test_variables = {
            "workspace_name": "Test Workspace",
            "button_link": self.settings.BASE_URL,
            "invitation_url": str(self.settings.BASE_URL),
        }

        try:
            success = email_service._send_db_template(data.recipient_email, template, test_variables)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send test email. Check SMTP configuration.",
                )

            return {"message": f"Test email sent to {data.recipient_email}"}

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error sending test email: {str(e)}",
            )

    def _check_workspace_access(self, group_id: UUID4) -> bool:
        """Check if user has access to workspace."""
        if self.user.admin:
            return True

        has_access = any(m.group_id == group_id for m in self.user.workspace_memberships)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this workspace",
            )
        return True

    def _check_admin_access(self, group_id: UUID4) -> bool:
        """Check if user has admin access to workspace."""
        if self.user.admin:
            return True

        for membership in self.user.workspace_memberships:
            if membership.group_id == group_id:
                if membership.workspace_role.value >= 4:  # ADMIN or OWNER
                    return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a workspace ADMIN or OWNER to manage email templates",
        )
