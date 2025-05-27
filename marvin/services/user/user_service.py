"""
This module defines the `UserService` for handling business logic related to
user management within the Marvin application.

It includes functionalities for managing user account locking status,
such as retrieving locked users, automatically resetting lockouts after a
configured duration, and manually locking or unlocking user accounts.
"""

from datetime import UTC, datetime  # For timestamping lock/unlock actions

from marvin.repos.repository_factory import AllRepositories  # Central repository access
from marvin.schemas.user.user import PrivateUser  # Pydantic schema for user data
from marvin.services import BaseService  # Base service class


class UserService(BaseService):
    """
    Service layer for user-related business logic.

    This service provides methods for managing user accounts, particularly
    focusing on account locking and unlocking mechanisms due to failed login
    attempts or administrative actions.
    """

    def __init__(self, repos: AllRepositories) -> None:
        """
        Initializes the UserService.

        Args:
            repos (AllRepositories): An instance of `AllRepositories` providing
                                     access to all data repositories, especially
                                     the users repository.
        """
        super().__init__()  # Initialize BaseService (for settings, logger)
        self.repos: AllRepositories = repos
        """Provides access to all data repositories."""
        # self.logger is inherited from BaseService

    def get_locked_users(self) -> list[PrivateUser]:
        """
        Retrieves a list of all users whose accounts are currently locked.

        A user is considered locked if their `locked_at` attribute is not None
        and the lockout period (defined by `is_locked` property on `PrivateUser` schema,
        which uses `SECURITY_USER_LOCKOUT_TIME` setting) has not yet expired.
        This method, however, relies on `self.repos.users.get_locked_users()`
        which might have a simpler definition of "locked" (e.g., just `locked_at` is not None).

        Returns:
            list[PrivateUser]: A list of Pydantic `PrivateUser` schemas for locked users.
        """
        self._logger.debug("Fetching list of all users currently marked as locked in the database.")
        # The repository method `get_locked_users` is responsible for the exact DB query.
        return self.repos.users.get_locked_users()

    def reset_locked_users(self, force: bool = False) -> int:
        """
        Resets the lockout status for users whose lockout period has expired, or all if forced.

        It queries the database for all users currently marked with a `locked_at` timestamp.
        For each such user, it checks if their lockout is still active (via `user.is_locked`).
        If `force` is True, or if the lockout is no longer active (i.e., expired),
        the user's account is unlocked by calling `self.unlock_user`.

        Args:
            force (bool, optional): If True, unlocks all users who have a `locked_at`
                                    timestamp, regardless of whether their lockout period
                                    has actually expired. Defaults to False.

        Returns:
            int: The number of users whose accounts were successfully unlocked.
        """
        # Get all users that have a `locked_at` timestamp (potential candidates for unlocking)
        candidate_locked_users = self.get_locked_users()
        self._logger.info(f"Found {len(candidate_locked_users)} users with a locked_at timestamp. Checking for reset eligibility.")

        unlocked_count = 0
        for user_schema in candidate_locked_users:  # Iterate through Pydantic schemas
            # `user_schema.is_locked` checks if the lockout duration is still active.
            # `user_schema.locked_at is not None` ensures we only process users who were actually locked.
            # Condition to unlock:
            #   - `force` is True (unlock regardless of expiry)
            #   OR
            #   - `user.is_locked` is False (lockout period has expired) AND `user.locked_at` is set (was actually locked)
            if force or (not user_schema.is_locked and user_schema.locked_at is not None):
                try:
                    self._logger.info(f"Unlocking user '{user_schema.username}' (ID: {user_schema.id}). Force: {force}.")
                    self.unlock_user(user_schema)  # Pass the Pydantic schema to unlock_user
                    unlocked_count += 1
                except Exception as e:
                    self._logger.error(f"Failed to unlock user '{user_schema.username}' (ID: {user_schema.id}): {e}", exc_info=True)

        self._logger.info(f"Finished resetting locked users. Total unlocked: {unlocked_count}.")
        return unlocked_count

    def lock_user(self, user_schema: PrivateUser) -> PrivateUser:  # Parameter is Pydantic schema
        """
        Locks a user's account by setting their `locked_at` timestamp to the current UTC time.

        The user's `login_attemps` are typically *not* reset by this method, as it's
        often called when login attempts have just reached a threshold.

        Args:
            user_schema (PrivateUser): The Pydantic schema of the user to lock.
                                       This object will be modified and used for the update.

        Returns:
            PrivateUser: The updated Pydantic schema of the user, reflecting the locked status.
        """
        self._logger.info(f"Locking user account for '{user_schema.username}' (ID: {user_schema.id}).")
        # Set the locked_at timestamp to current UTC time
        user_schema.locked_at = datetime.now(UTC)
        # Persist the changes using the user repository.
        # The `update` method of the repository expects the user ID and the data to update.
        # Pass the updated schema (or its dict representation) for the update.
        return self.repos.users.update(user_schema.id, user_schema)  # Assumes repo.update takes schema/dict

    def unlock_user(self, user_schema: PrivateUser) -> PrivateUser:  # Parameter is Pydantic schema
        """
        Unlocks a user's account by clearing their `locked_at` timestamp and resetting `login_attemps`.

        Args:
            user_schema (PrivateUser): The Pydantic schema of the user to unlock.
                                       This object will be modified and used for the update.

        Returns:
            PrivateUser: The updated Pydantic schema of the user, reflecting the unlocked status.
        """
        self._logger.info(f"Unlocking user account for '{user_schema.username}' (ID: {user_schema.id}).")
        # Clear the locked_at timestamp
        user_schema.locked_at = None
        # Reset failed login attempts count
        user_schema.login_attemps = 0
        # Persist the changes using the user repository
        return self.repos.users.update(user_schema.id, user_schema)  # Assumes repo.update takes schema/dict
