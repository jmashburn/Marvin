"""
This module defines the `PasswordResetService` for handling the business logic
associated with user password reset requests within the Marvin application.

It includes functionalities for generating password reset tokens, sending reset
emails to users, and validating tokens to allow users to set a new password.
"""

from fastapi import HTTPException, status  # For raising HTTP exceptions
from sqlalchemy.orm.session import Session  # SQLAlchemy session type

# Marvin core, database, repository, schema, and service imports
from marvin.core.security import hash_password, url_safe_token  # Security utilities
from marvin.db.models.users.users import AuthMethod  # Enum for authentication methods
from marvin.repos.all_repositories import AllRepositories, get_repositories  # Central repository access
from marvin.schemas.user.password import PasswordResetToken as PasswordResetTokenSchema  # Pydantic schema

# Note: PasswordResetTokenSchema is used for `generate_reset_token` return and `save_token`.
# It contains `email` and `token`. The DB model `PasswordResetModel` might store `user_id` and `token`.
# This could imply a slight mismatch or that `PasswordResetTokenSchema` is also used for DB creation payload.
# For DB creation, a schema like `SavePasswordResetToken` (with user_id, token) is used in other files.
# Let's assume `PasswordResetTokenSchema` is flexible enough or that the repo handles it.
from marvin.services import BaseService  # Base service class
from marvin.services.email.email_service import EmailService  # Email sending service


class PasswordResetService(BaseService):
    """
    Service layer for managing password reset processes.

    This service handles the generation of secure password reset tokens,
    dispatching password reset emails, and the final step of resetting a user's
    password after successful token validation.
    """

    def __init__(self, session: Session) -> None:
        """
        Initializes the PasswordResetService.

        Args:
            session (Session): The SQLAlchemy database session to be used for
                               repository initialization. Repositories are initialized
                               without group scoping (`group_id=None`) as password reset
                               operations are typically system-wide by email/user ID.
        """
        super().__init__()  # Initialize BaseService (for settings, logger)
        self.db: AllRepositories = get_repositories(session, group_id=None)  # Use non-scoped repositories
        # self.logger is inherited from BaseService

    def generate_reset_token(self, email: str) -> PasswordResetTokenSchema | None:
        """
        Generates a password reset token for a user identified by their email.

        It first checks if the user exists and is not managed by an external
        authentication system like LDAP. If eligible, a secure token is generated
        and stored in the database, associated with the user.

        To prevent user enumeration, this method returns `None` both if the user
        doesn't exist and if a token cannot be generated (e.g., LDAP user),
        rather than raising distinct errors.

        Args:
            email (str): The email address of the user requesting a password reset.

        Returns:
            PasswordResetTokenSchema | None: A Pydantic schema containing the user's email
                                            and the generated token if successful,
                                            otherwise None.
        """
        # Find the user by email (case-insensitive search)
        user = self.db.users.get_one(email, key="email", any_case=True)

        if user is None:
            self.logger.warning(f"Password reset attempt for non-existent email: {email}")
            # Do not confirm to the client that the email doesn't exist (prevents user enumeration).
            return None

        # Check if user's password is managed externally (e.g., LDAP)
        # The original check `user.password == "LDAP"` is brittle; relying on `auth_method` is better.
        if user.auth_method == AuthMethod.LDAP:
            self.logger.warning(f"Password reset attempt for LDAP user: {email}. Denied.")
            return None  # LDAP users cannot reset passwords via this Marvin mechanism.

        # Generate a cryptographically secure URL-safe token
        token_string = url_safe_token()

        # Prepare data for storing the token in the database.
        # The DB model `PasswordResetModel` likely stores `user_id` and `token`.
        # The `PasswordResetTokenSchema` (which includes `email` and `token`) might be
        # what `self.db.tokens_pw_reset.create` expects if it handles the user lookup by email,
        # or if it's adapted to take `user_id` from the `user` object.
        # Assuming `create` can handle a schema that includes `user_id` and `token`.
        # A more explicit schema like `SavePasswordResetToken(user_id=user.id, token=token_string)`
        # would be clearer if that's what the repository expects.
        # The original code used `PasswordResetToken(user_id=user.id, token=token)`.
        # Let's assume PasswordResetToken Pydantic model used for creation can take user_id.
        # However, PasswordResetToken as defined inherits email and adds token.
        # This implies PasswordResetToken is more for response.
        # Using a dict for clarity or a dedicated Create schema.
        from marvin.schemas.user.password import SavePasswordResetToken  # Ensure this schema is appropriate

        token_save_data = SavePasswordResetToken(user_id=user.id, token=token_string)

        created_token_db_model = self.db.tokens_pw_reset.create(token_save_data)

        # Return a schema that includes the email and token for the email sending step.
        return PasswordResetTokenSchema(email=email, token=created_token_db_model.token)

    def send_reset_email(self, email: str, accept_language: str | None = None) -> bool:  # Return bool for success
        """
        Generates a password reset token and sends it to the user via email.

        If token generation is successful (user exists and is eligible), an email
        containing a password reset link (with the token) is sent.

        Args:
            email (str): The user's email address.
            accept_language (str | None, optional): Preferred language for the email,
                                                    extracted from 'Accept-Language' header.
                                                    Defaults to None.

        Returns:
            bool: True if the email was dispatched successfully, False otherwise.
                  Note: This does not confirm if the email address exists, to prevent enumeration.

        Raises:
            HTTPException (500 Internal Server Error): If email sending fails due to
                                                      an unexpected server error.
        """
        # Generate the password reset token. This also handles checks for user existence/LDAP.
        token_entry_schema = self.generate_reset_token(email)

        if token_entry_schema is None:
            # Token generation failed (e.g., user not found, LDAP user).
            # Log already happened in generate_reset_token. Silently return to prevent enumeration.
            return False  # Indicate that no email was sent.

        # Initialize email service with locale preference
        email_service = EmailService(locale=accept_language)
        # Construct the full password reset URL
        reset_url = f"{self.settings.BASE_URL}/reset-password/?token={token_entry_schema.token}"

        try:
            # Send the "forgot password" email
            success = email_service.send_forgot_password(email, reset_url)
            if success:
                self.logger.info(f"Password reset email successfully dispatched for: {email}")
            else:
                self.logger.error(f"Password reset email failed to dispatch for: {email} (EmailService returned False)")
            return success
        except Exception as e:
            self.logger.exception(f"Failed to send password reset email to {email} due to an unexpected error: {e}")
            # Re-raise as HTTPException to be handled by FastAPI error middleware
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email due to a server error.",
            ) from e

    def reset_password(self, token: str, new_password: str) -> bool:  # Return bool for success
        """
        Resets a user's password using a provided reset token and new password.

        Validates the token, updates the user's password with the new (hashed) password,
        and then deletes the used token from the database.

        Args:
            token (str): The password reset token received by the user.
            new_password (str): The new plaintext password chosen by the user.

        Returns:
            bool: True if the password was successfully reset.

        Raises:
            HTTPException (400 Bad Request): If the token is invalid or the new password
                                           cannot be set (e.g., validation fails, though
                                           Pydantic schema for ResetPassword should handle this).
        """
        # Validate the provided token by fetching its entry from the database
        # The repository's get_one method should use "token" as the lookup key here.
        token_entry_db = self.db.tokens_pw_reset.get_one(token, key="token")

        if token_entry_db is None:
            self.logger.warning(f"Password reset attempt with invalid or expired token: {token}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired password reset token.")

        # Fetch the user associated with the token
        # `token_entry_db.user_id` should be available from the schema/model used by the repo.
        user_to_update = self.db.users.get_one(token_entry_db.user_id)  # Assuming user_id is on token_entry_db
        if not user_to_update:  # Should not happen if token is valid and DB is consistent
            self.logger.error(f"User not found for valid password reset token. User ID: {token_entry_db.user_id}, Token: {token}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User associated with token not found.")

        # Hash the new password
        hashed_new_password = hash_password(new_password)

        # Update the user's password in the database
        # `update_password` is a method on RepositoryUsers.
        updated_user_schema = self.db.users.update_password(user_to_update.id, hashed_new_password)

        # Verify if the password update was successful (optional, if repo method confirms)
        # The original code `if new_user.password != password_hash:` is problematic as
        # `updated_user_schema.password` (from UserRead/PrivateUser) would still be the hashed one.
        # A better check is if the update operation itself succeeded, or if a re-fetch and verify is needed.
        # For now, assuming `update_password` raises on failure or returns a clear status.
        # If `update_password` returns the updated user schema:
        if updated_user_schema.password != hashed_new_password:  # This check may not be reliable if schema hides password
            self.logger.error(f"Password update failed for user {user_to_update.username} despite repository indicating success.")
            # This indicates an internal logic issue if reached.
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Password update confirmation failed.")

        # Delete the used password reset token from the database
        # `delete` method on repo needs value and key. `token_entry_db.token` is the value.
        self.db.tokens_pw_reset.delete(token_entry_db.token, match_key="token")
        self.logger.info(f"Password successfully reset for user {user_to_update.username}. Token {token} deleted.")

        return True
