"""
This module provides base controller classes for FastAPI routes in Marvin.

These controllers offer common dependencies and functionalities like database
session management, repository access, settings, logging, user authentication,
and event publishing, intended to be inherited by specific route controllers.
"""
from abc import ABC # Abstract Base Class
from logging import Logger

from fastapi import Depends, HTTPException # Standard FastAPI dependencies and exceptions
from pydantic import UUID4, ConfigDict # Pydantic types for validation and config
from sqlalchemy.orm import Session # SQLAlchemy session type

# Marvin core components
from marvin.core.config import get_app_dirs, get_app_settings
from marvin.core.dependencies import get_admin_user, get_current_user # User dependency injectors
from marvin.core.exceptions import registered_exceptions # Pre-defined exception messages
from marvin.core.root_logger import get_logger # Application logger
from marvin.core.settings import AppSettings
from marvin.core.settings.directories import AppDirectories
from marvin.db.db_setup import generate_session # Database session generator
from marvin.repos._utils import NOT_SET, NotSet # Sentinel for unset group_id
from marvin.repos.all_repositories import AllRepositories # Central repository access
from marvin.routes._base.checks import OperationChecks # Permission checks
from marvin.schemas.group import GroupRead # Pydantic schemas
from marvin.schemas.user import PrivateUser
from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import (
    EventDocumentDataBase, # Base for event data
    EventTypes,            # Enum for event types
)


class _BaseController(ABC):
    """
    An abstract base controller providing common dependencies and properties.

    This class should not be used directly in routes but should be inherited by
    other base or specific controllers. It initializes lazy-loaded properties for
    database session, repositories, settings, directories, and logger.
    """
    # FastAPI dependency to inject a SQLAlchemy session into controller methods
    session: Session = Depends(generate_session)

    # Private attributes for lazy loading, initialized to None
    _repos: AllRepositories | None = None
    _settings: AppSettings | None = None
    _directories: AppDirectories | None = None
    _logger: Logger | None = None

    @property
    def repos(self) -> AllRepositories:
        """
        Provides access to all data repositories, initialized on first access.
        The repositories are scoped by `self.group_id`.
        """
        if self._repos is None: # Lazy initialization
            self._repos = AllRepositories(self.session, group_id=self.group_id)
        return self._repos

    @property
    def settings(self) -> AppSettings:
        """Provides access to the application settings, loaded on first access."""
        if self._settings is None: # Lazy initialization
            self._settings = get_app_settings()
        return self._settings

    @property
    def directories(self) -> AppDirectories:
        """Provides access to application directories, loaded on first access."""
        if self._directories is None: # Lazy initialization
            self._directories = get_app_dirs()
        return self._directories

    @property
    def logger(self) -> Logger:
        """Provides access to the application logger, initialized on first access."""
        if self._logger is None: # Lazy initialization
            self._logger = get_logger()
        return self._logger

    @property
    def group_id(self) -> UUID4 | None | NotSet:
        """
        The group ID to scope repository operations to.

        Defaults to `NOT_SET`, indicating no specific group scope unless overridden
        by a subclass (e.g., `BaseUserController` which gets it from the current user).
        """
        return NOT_SET

    # Pydantic model configuration to allow arbitrary types for properties like `session`
    model_config = ConfigDict(arbitrary_types_allowed=True)


class BasePublicController(_BaseController):
    """
    Base controller for public routes that do not require user authentication.

    Inherits common dependencies from `_BaseController`. The `group_id` for
    repositories will default to `NOT_SET` unless there's a specific need
    to scope public data (which would be unusual).
    """
    pass # No additional functionalities beyond _BaseController for now


class BaseUserController(_BaseController):
    """
    Base controller for routes that require an authenticated user.

    Injects the current authenticated user and provides access to their group ID
    and group details. It also initializes `OperationChecks` for permission handling.
    """
    # FastAPI dependency to inject the currently authenticated user
    user: PrivateUser = Depends(get_current_user)

    _checks: OperationChecks | None = None # For lazy initialization of OperationChecks

    def registered_exceptions(self, ex: type[Exception]) -> str:
        """
        Retrieves a user-friendly message for a registered exception type.

        Args:
            ex (type[Exception]): The type of the exception that occurred.

        Returns:
            str: A predefined message for the exception, or a generic error message.
        """
        # Combine system-wide registered exceptions with any controller-specific ones if needed
        registered_exception_map = {
            **registered_exceptions(),
            # ... any controller specific exceptions could be added here
        }
        return registered_exception_map.get(ex, "An unexpected error occurred during your request.")

    @property
    def group_id(self) -> UUID4:
        """
        The group ID of the currently authenticated user.
        This will scope repository operations within `self.repos` to the user's group.
        """
        if self.user and self.user.group_id: # Ensure user and group_id are available
            return self.user.group_id
        # This case should ideally not be reached if get_current_user ensures user has a group.
        # Handling it defensively:
        raise HTTPException(status_code=403, detail="User is not associated with a group.")


    @property
    def group(self) -> GroupRead:
        """
        The Pydantic schema of the group the current user belongs to.
        Fetched using `self.repos` which is already scoped by `self.group_id`.
        """
        group_data = self.repos.groups.get_one(self.group_id) # group_id from property above
        if not group_data:
            # This would be unusual if group_id is valid.
            raise HTTPException(status_code=404, detail=f"Group with ID {self.group_id} not found.")
        return group_data


    @property
    def checks(self) -> OperationChecks:
        """
        Provides an `OperationChecks` instance for performing permission checks
        based on the current authenticated user. Initialized on first access.
        """
        if self._checks is None: # Lazy initialization
            self._checks = OperationChecks(self.user)
        return self._checks


class BaseAdminController(BaseUserController):
    """
    Base controller for routes that require administrative privileges.

    Injects an admin user (verified by `get_admin_user` dependency).
    Overrides `repos` to ensure that admin users operate without group scoping
    (i.e., `group_id=None`), allowing them system-wide access.
    """
    # FastAPI dependency to inject an admin user; raises 403 if user is not admin
    user: PrivateUser = Depends(get_admin_user)

    @property
    def repos(self) -> AllRepositories:
        """
        Provides access to all data repositories, initialized on first access.
        For admin users, repositories are explicitly initialized with `group_id=None`
        to grant system-wide access, overriding any group ID from the user object.
        """
        if self._repos is None: # Lazy initialization
            # Admin controllers operate with system-wide scope
            self._repos = AllRepositories(self.session, group_id=None)
        return self._repos


class BaseCrudController(BaseUserController):
    """
    Base controller for CRUD operations, extending `BaseUserController`.

    Provides an `EventBusService` dependency and a helper method `publish_event`
    for dispatching events related to CRUD actions.
    """
    # FastAPI dependency to inject the EventBusService
    event_bus: EventBusService = Depends(EventBusService.as_dependency)

    def publish_event(
        self,
        event_type: EventTypes,
        document_data: EventDocumentDataBase,
        message: str = "",
    ) -> None:
        """
        Publishes an event to the application's event bus.

        Args:
            event_type (EventTypes): The type of event to publish (e.g., ITEM_CREATED).
            document_data (EventDocumentDataBase): The data associated with the event,
                                                   often the created/updated/deleted entity.
            message (str, optional): An optional descriptive message for the event.
                                     Defaults to "".
        """
        self.event_bus.dispatch(
            event_type=event_type,
            document_data=document_data, # This should be the Pydantic model of the entity
            message=message,
        )
