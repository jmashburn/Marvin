from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, status

from marvin.core.security import url_safe_token
from marvin.routes._base import BaseUserController, controller
from marvin.schemas.group.invite_token import (
    InviteTokenCreate,
    EmailInitationResponse,
    EmailInvitation,
    InviteTokenRead,
    InviteTokenUpdate,
)
from marvin.schemas.response.pagination import PaginationQuery
from marvin.services.email.email_service import EmailService

router = APIRouter(prefix="/groups/invitations", tags=["Groups: Invitations"])


@controller(router)
class GroupInvitationsController(BaseUserController):
    @router.get("", response_model=list[InviteTokenRead])
    def get_invite_tokens(self):
        return self.repos.group_invite_tokens.page_all(PaginationQuery(page=1, per_page=-1)).items

    @router.post("", response_model=InviteTokenRead, status_code=status.HTTP_201_CREATED)
    def create_invite_token(self, body: InviteTokenCreate):
        if not self.user.can_invite:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="User is not allowed to create invite tokens",
            )

        body.group_id = body.group_id or self.group_id

        if not self.user.admin and (body.group_id != self.group_id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Only admins can create invite tokens for other groups",
            )

        token = InviteTokenUpdate(uses_left=body.uses, group_id=body.group_id, token=url_safe_token())
        return self.repos.group_invite_tokens.create(token)

    @router.post("/email", response_model=EmailInitationResponse)
    def email_invitation(
        self,
        invite: EmailInvitation,
        accept_language: Annotated[str | None, Header()] = None,
    ):
        email_service = EmailService(locale=accept_language)
        url = f"{self.settings.BASE_URL}/register?token={invite.token}"

        success = False
        error = None
        try:
            success = email_service.send_invitation(address=invite.email, invitation_url=url)
        except Exception as e:
            error = str(e)

        return EmailInitationResponse(success=success, error=error)
