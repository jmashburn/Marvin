"""
This module defines the FastAPI controller for managing user-specific API tokens
(long-lived tokens) within the Marvin application.

It provides endpoints for authenticated users to create and delete their own API tokens.
"""

from datetime import timedelta  # For setting token expiration

from fastapi import HTTPException, status  # APIRouter for instantiation
from pydantic import UUID4  # For type hinting token_id, though it's int in delete method currently

# Marvin core components, schemas, and base controller
from marvin.core.security import create_access_token  # Utility for generating access tokens
from marvin.routes._base import BaseUserController, controller  # Base controller for user-authenticated routes
from marvin.routes._base.routers import UserAPIRouter  # Specific router for user-authenticated endpoints
from marvin.schemas.user import (  # Pydantic schemas related to API tokens
    LongLiveTokenCreate,
    LongLiveTokenCreateResponse,  # Response schema after creating a token, includes the token string
    LongLiveTokenRead,  # Schema for reading token details (excluding the token string itself)
    TokenCreate,  # Internal schema for creating token model in DB
    TokenResponseDelete,  # Response schema after deleting a token
)

# Router for user API token management.
# All routes will be under /users/api-tokens due to UserAPIRouter prefix and this prefix.
# Using UserAPIRouter ensures these endpoints require user authentication.
router = UserAPIRouter(prefix="/api-tokens", tags=["User: Self Service"])  # Corrected prefix to be more specific


@controller(router)  # Registers this class-based view with the defined router
class UserApiTokensController(BaseUserController):
    """
    Controller for managing user-specific API tokens (long-lived tokens).

    Authenticated users can use these endpoints to create new API tokens for
    programmatic access and to delete their existing tokens.
    """

    @router.post(
        "",
        status_code=status.HTTP_201_CREATED,
        response_model=LongLiveTokenCreateResponse,
        summary="Create an API Token",
    )
    def create_api_token(
        self,
        token_params: LongLiveTokenCreate,  # Request body with name and optional integration_id
    ) -> LongLiveTokenCreateResponse:  # Return type includes the generated token string
        """
        Creates a new long-lived API token for the authenticated user.

        The token is generated with a long expiration period (e.g., 5 years) and
        is associated with the current user. The actual token string is returned
        only upon creation.

        Args:
            token_params (LongLiveTokenCreate): Pydantic schema containing the desired
                                                `name` and optional `integration_id` for the token.

        Returns:
            LongLiveTokenCreateResponse: Pydantic schema containing the details of the
                                         created token, including the generated `token` string.
        """
        # Prepare data for JWT token generation
        jwt_token_payload = {
            "long_token": True,  # Flag indicating this is a long-lived token
            "id": str(self.user.id),  # User ID associated with the token
            "name": token_params.name,  # User-defined name for the token
            "integration_id": token_params.integration_id,  # Optional integration identifier
        }

        # Define a long expiration period for the token (e.g., 5 years)
        five_years_delta = timedelta(days=1825)
        # Generate the actual token string using the security utility
        generated_token_string = create_access_token(jwt_token_payload, five_years_delta)

        # Prepare data for saving the token metadata to the database
        # Note: The `TokenCreate` schema is used here for DB storage, which includes the token string.
        token_to_store_in_db = TokenCreate(
            name=token_params.name,
            token=generated_token_string,  # The generated JWT
            user_id=self.user.id,  # Associate with the current user
            integration_id=token_params.integration_id,
        )

        # Create the token entry in the database using the api_tokens repository
        # `self.repos.api_tokens` is scoped to the current user's group, but tokens are user-specific.
        # This implies `api_tokens` repository handles user-level creation correctly even if group-scoped.
        new_token_db_entry = self.repos.api_tokens.create(token_to_store_in_db)

        # The response should include the generated token string.
        # `LongLiveTokenCreateResponse` should be designed to include `token` field.
        # Assuming `new_token_db_entry` (which is likely `LongLiveTokenRead` from repo)
        # doesn't directly contain the token string for security in reads,
        # we construct the response with the generated token.
        if new_token_db_entry:  # Check if DB creation was successful
            self.logger.info(f"API Token '{token_params.name}' created for user ID {self.user.id}")
            return LongLiveTokenCreateResponse(
                id=new_token_db_entry.id,
                name=new_token_db_entry.name,
                integration_id=new_token_db_entry.integration_id,
                user_id=new_token_db_entry.user_id,
                created_at=new_token_db_entry.created_at,
                updated_at=new_token_db_entry.updated_at,
                token=generated_token_string,  # Return the actual token string on creation
            )
        else:
            # This path should ideally not be reached if create raises an exception on failure.
            self.logger.error(f"API Token creation failed for user ID {self.user.id} after DB operation.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API token after database operation.",
            )

    @router.delete("/{token_id}", response_model=TokenResponseDelete, summary="Delete an API Token")
    def delete_api_token(self, token_id: UUID4) -> TokenResponseDelete:  # Changed token_id type to UUID4
        """
        Deletes a specific API token belonging to the authenticated user.

        Users can only delete their own API tokens.

        Args:
            token_id (UUID4): The ID of the API token to be deleted.

        Returns:
            TokenResponseDelete: A Pydantic model confirming the name of the deleted token.

        Raises:
            HTTPException (404 Not Found): If the token with the given ID is not found.
            HTTPException (403 Forbidden): If the user attempts to delete a token
                                         that does not belong to them.
        """
        # Retrieve the token details first to ensure it exists and belongs to the user.
        # `self.repos.api_tokens` is group-scoped, but token ownership is by user.
        # The `get_one` here should ideally also check user ownership if not handled by RLS or repo logic.
        token_to_delete: LongLiveTokenRead | None = self.repos.api_tokens.get_one(token_id)

        if not token_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"API token with ID '{token_id}' not found.")

        # Verify that the token belongs to the currently authenticated user.
        # `LongLiveTokenRead` schema needs to expose `user_id` or equivalent for this check.
        # Assuming `token_to_delete.user_id` is available from the schema.
        if not hasattr(token_to_delete, "user_id") or token_to_delete.user_id != self.user.id:
            # If user_id is not on LongLiveTokenRead, or if it doesn't match, then Forbidden.
            # The original code compared `token.user.email == self.user.email`.
            # Comparing IDs is generally more robust if user_id is available on token schema.
            # If checking by email (as original):
            # if not hasattr(token_to_delete, 'user') or token_to_delete.user.email != self.user.email:
            self.logger.warning(f"User {self.user.id} attempted to delete token {token_id} not belonging to them.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not authorized to delete this API token.")

        # Proceed with deletion
        deleted_token_details = self.repos.api_tokens.delete(token_id)  # `delete` returns the deleted item's schema
        self.logger.info(f"API Token ID {token_id} (Name: '{deleted_token_details.name}') deleted by user ID {self.user.id}")

        return TokenResponseDelete(token_delete=deleted_token_details.name)  # Return name of deleted token
