"""
This module defines the `GroupService` for handling business logic
related to user groups within the Marvin application.

Currently, it primarily provides functionality for creating new groups along
with their associated default preferences.
"""

from pydantic import UUID4  # For UUID type hinting

# Marvin core and repository imports
from marvin.core.config import get_app_settings  # Access application settings
from marvin.repos.all_repositories import get_repositories  # Factory for AllRepositories
from marvin.repos.repository_factory import AllRepositories  # Central repository access
from marvin.schemas.group import GroupCreate, GroupRead  # Pydantic schemas for Group
from marvin.schemas.group.preferences import GroupPreferencesCreate  # Schema for creating group preferences
from marvin.services import BaseService  # Base service class


class GroupService(BaseService):
    """
    Service layer for managing group-related business logic.

    This service encapsulates operations such as group creation, ensuring that
    necessary associated data like group preferences are also initialized.
    Instance methods would typically operate within the context of a specific
    `group_id` and use a pre-configured `AllRepositories` instance.
    """

    def __init__(self, group_id: UUID4, repos: AllRepositories) -> None:
        """
        Initializes the GroupService for a specific group context.

        Args:
            group_id (UUID4): The unique identifier of the group this service instance
                              will primarily interact with or be scoped to.
            repos (AllRepositories): An instance of `AllRepositories` providing
                                     access to all data repositories, potentially already
                                     scoped or to be scoped as needed by service methods.
        """
        super().__init__()  # Initialize BaseService (likely for settings, logger)
        self.group_id: UUID4 = group_id
        """The ID of the group this service instance is associated with."""
        self.repos: AllRepositories = repos
        """Provides access to all data repositories."""
        # self.logger is inherited from BaseService

    @staticmethod
    def create_group(
        repos: AllRepositories,  # Repositories instance (typically non-group-scoped for creating a new group)
        group_data: GroupCreate,  # Renamed `group` to `group_data` for clarity
        prefs_data: GroupPreferencesCreate | None = None,  # Renamed `prefs` to `prefs_data`
    ) -> GroupRead:  # Return type is the Pydantic schema for reading a group
        """
        Creates a new group in the database along with its default preferences.

        This static method handles the creation of a `Groups` entity and its associated
        `GroupPreferencesModel` entity in a single operation. If preferences data
        is not provided, default preferences are created for the new group.

        Args:
            repos (AllRepositories): An instance of `AllRepositories`, typically initialized
                                     without a specific group_id to allow creation of new groups.
            group_data (GroupCreate): Pydantic schema containing the data for the new group
                                      (e.g., name).
            prefs_data (GroupPreferencesCreate | None, optional): Optional Pydantic schema
                containing initial preference data for the group. If None, default
                preferences are created. Defaults to None.

        Returns:
            GroupRead: A Pydantic schema representing the newly created group,
                       including its ID and initialized preferences.
        """
        # Create the main group entry using the groups repository
        # The `repos.groups.create` method is expected to handle slug generation etc.
        new_group_schema: GroupRead = repos.groups.create(group_data)

        # Prepare preferences data
        if prefs_data is None:
            # If no specific preferences are provided, create default preferences linked to the new group's ID.
            final_prefs_data = GroupPreferencesCreate(group_id=new_group_schema.id)
        else:
            # If preferences data is provided, ensure it's linked to the new group's ID.
            final_prefs_data = prefs_data
            final_prefs_data.group_id = new_group_schema.id  # Override or set group_id

        # Obtain a repository instance scoped to the newly created group's ID
        # This is necessary because group_preferences repository is a GroupRepositoryGeneric
        # and requires a group_id for its operations.
        group_specific_repos = get_repositories(repos.session, group_id=new_group_schema.id)

        # Create the group preferences entry using the group-scoped repository
        created_group_preferences = group_specific_repos.group_preferences.create(final_prefs_data)

        # Application settings might be used here for other default initializations if needed.
        _ = get_app_settings()  # settings variable was initialized but not used further.

        # Attach the created preferences to the group schema to be returned.
        # The `new_group_schema` is a Pydantic model; direct attribute assignment works if configured.
        # Ensure `GroupRead` schema has a `preferences` field of appropriate type (e.g., `GroupPreferencesRead`).
        new_group_schema.preferences = created_group_preferences

        return new_group_schema
