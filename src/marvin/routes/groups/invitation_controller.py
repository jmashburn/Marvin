"""
This module defines the FastAPI controller for managing group invitations
within the Marvin application.

It provides endpoints for creating and listing group invitation tokens,
and for sending email invitations containing these tokens.
"""

from typing import Annotated  # For type hinting with FastAPI Header

from fastapi import APIRouter, Header, Depends, HTTPException, status  # Core FastAPI components

# Marvin core, schemas, services, and base controller
from marvin.core.security import url_safe_token  # For generating secure tokens
from marvin.routes._base import BaseUserController, controller  # Base controller for user-authenticated routes
from marvin.schemas.group.invite_token import (  # Pydantic schemas for invite tokens
    EmailInitationResponse,
    EmailInvitation,
    InviteTokenCreate,
    InviteTokenRead,
    InviteTokenSave,
    InviteTokenPagination,  # For paginated responses
    InviteTokenSummary,
    # InviteTokenUpdate, # InviteTokenUpdate was imported but not used
)
from marvin.schemas.mapper import cast  # Utility for casting between schema types
from marvin.schemas.response.pagination import PaginationQuery  # For pagination parameters
from marvin.services.email.email_service import EmailService  # Service for sending emails

# APIRouter for group invitations, prefixed accordingly.
# All routes here will be under /groups/invitations based on router prefix in main app and this.
router = APIRouter(prefix="/groups/invitations")


@controller(router)
class GroupInvitationsController(BaseUserController):
    """
    Controller for managing group invitation tokens and sending email invitations.

    Provides functionality to create and list invitation tokens for groups,
    and to email these invitations to prospective users. Access is restricted
    based on user permissions (e.g., `can_invite`).
    """

    @router.get("", response_model=InviteTokenPagination, summary="List Group Invite Tokens")
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery)) -> InviteTokenPagination:
        """
        Retrieves all active invitation tokens for the current user's group.

        Note: This endpoint currently fetches all tokens (per_page=-1) for the group
        associated with the authenticated user via `self.repos.group_invite_tokens`
        which is already group-scoped by `BaseUserController`.

        Returns:
            InviteTokenPagination: Paginated list of invite token summeries.
        """
        # `self.repos.group_invite_tokens` is automatically scoped to the user's group
        # by `BaseUserController`'s `repos` property.
        # Fetch all items by setting per_page to -1 (or a very large number if -1 isn't supported by pagination).
        # `self.repo` is already group-scoped.
        paginated_response = self.repos.group_invite_tokens.page_all(
            pagination=q,
            override_schema=InviteTokenRead,  # Serialize items using InviteTokenPagination
        )
        # Set HATEOAS pagination guide URLs
        paginated_response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return paginated_response

    @router.post("", response_model=InviteTokenSummary, status_code=status.HTTP_201_CREATED, summary="Create an Invite Token")
    def create_invite_token(self, token_data: InviteTokenCreate) -> InviteTokenSummary:  # Renamed `token` to `token_data`
        """
        Creates a new invitation token for a group.

        Args:
            token_data (InviteTokenCreate): Pydantic schema containing the data for the new token,
                                         such as `uses_left`.

        Returns:
            InviteTokenRead: The Pydantic schema of the newly created invitation token.

        Raises:
            HTTPException (403 Forbidden): If the user lacks permission to create tokens
                                         or to create tokens for the specified group.
        """
        # Check if the user has permission to invite
        self.checks.can_invite()

        # Prepare the final token data for creation, generating a secure token string
        # Note: The input `token_data` (InviteTokenCreate) has `uses`, but the model uses `uses_left`.
        # Assuming `token_data.uses` is meant for `uses_left`.
        final_token_payload = InviteTokenCreate(
            uses_left=token_data.uses_left,  # uses_left from input schema
        )

        save_data = cast(final_token_payload, InviteTokenSave, token=url_safe_token(), group_id=self.group_id)
        # Create the token using the group_invite_tokens repository
        created_token = self.repos.group_invite_tokens.create(save_data)
        self.logger.info(f"Invite token created by user {self.user.username} for group {self.group_id}")
        return created_token

    @router.post("/email", response_model=EmailInitationResponse, summary="Send Email Invitation")
    def email_invitation(
        self,
        invite_data: EmailInvitation,  # Renamed `invite` to `invite_data`
        accept_language: Annotated[str | None, Header()] = None,  # Optional language preference
    ) -> EmailInitationResponse:
        """
        Sends an email invitation containing a group invite token.

        The email is sent to the specified address with a registration link
        that includes the provided token. The email content may be localized.

        Args:
            invite_data (EmailInvitation): Pydantic schema containing the recipient `email`
                                           and the `token` string to include in the invitation.
            accept_language (str | None, optional): The preferred language for the email,
                                                    extracted from the 'Accept-Language' header.
                                                    Defaults to None (system default language).

        Returns:
            EmailInitationResponse: A Pydantic model indicating whether the email was
                                    sent successfully and any error message if it failed.
        """
        self.checks.can_invite()  # Ensure user has permission to invite

        if not self.settings.SMTP_ENABLED:
            # If SMTP is not enabled, raise an error
            self.logger.error("SMTP service is not enabled, cannot send email invitations.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Email service is currently unavailable. Please try again later."
            )

        token = self.repos.group_invite_tokens.get_one(invite_data.token, "token")  # Fetch the token by its string value

        if not token or token.uses_left <= 0:
            # If the token does not exist or has no uses left, raise an error
            self.logger.error(f"Invalid or expired token: {invite_data.token}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The provided invitation token is invalid or has expired.")

        email_service = EmailService(locale=accept_language)  # Initialize email service with locale

        # Construct the full registration URL including the token
        registration_url = f"{self.settings.BASE_URL}/register?token={invite_data.token}"

        email_sent_successfully = False  # Default status
        error_message: str | None = None  # Default error message

        try:
            # Attempt to send the invitation email
            email_sent_successfully = email_service.send_invitation(recipient_address=invite_data.email, invitation_url=registration_url)
            if email_sent_successfully:
                self.logger.info(f"Invitation email sent to {invite_data.email} with token {invite_data.token}")
            else:
                # If service returns False without an exception
                error_message = "Email service reported failure to send invitation without raising an exception."
                self.logger.warning(f"Failed to send invitation email to {invite_data.email} (service returned false). Token: {invite_data.token}")

        except Exception as e:
            # Log the exception and capture the error message
            self.logger.error(f"Error sending invitation email to {invite_data.email} with token {invite_data.token}: {e}")
            error_message = str(e)

        return EmailInitationResponse(success=email_sent_successfully, error=error_message)
