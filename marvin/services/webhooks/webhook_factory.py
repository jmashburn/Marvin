"""
This module defines the `AllWebhooks` factory class, which serves as a
centralized access point or registry for different types of webhook runners
or handlers within the Marvin application.

It allows for on-demand instantiation of specific webhook handlers
(e.g., `GenericWebhook`, `UserWebhook`) associated with a given database
session and an optional group context.
"""

from functools import cached_property  # For lazy-loading webhook handler instances

from pydantic import UUID4  # For UUID type hinting
from sqlalchemy.orm import Session  # For type hinting SQLAlchemy Session

# `NOT_SET` and `NotSet` are imported for handling optional group_id.
from ...repos._utils import NOT_SET, NotSet

# Import specific webhook handler implementations
from .base_webhook import BaseWebhook  # Base class for type hinting if needed
from .generic import GenericWebhook
from .user import UserWebhook


class AllWebhooks:
    """
    A factory and registry class for accessing various webhook handler instances.

    This class provides `cached_property` methods for different types of webhook
    handlers (e.g., 'generic', 'user'). When a handler type is first accessed,
    it is instantiated with the session and group ID provided to `AllWebhooks`
    and then cached for subsequent use within the same `AllWebhooks` instance.

    This pattern centralizes the creation and access of webhook handlers, making
    it easier for services like `WebhookEventListener` to obtain the correct handler
    based on a webhook's configured type.
    """

    session: Session
    """The SQLAlchemy session passed to instantiated webhook handlers."""
    group_id: UUID4 | None | NotSet  # Changed to reflect actual usage
    """
    The group ID to scope webhook handlers to. Can be a UUID, None (for no specific group),
    or NOT_SET (if group context is truly optional or determined differently by handlers).
    """

    def __init__(
        self,
        session: Session,
        *,  # Keyword-only arguments follow
        group_id: UUID4 | None | NotSet = NOT_SET,
    ) -> None:
        """
        Initializes the AllWebhooks factory.

        Args:
            session (Session): The SQLAlchemy database session that will be passed
                               to instantiated webhook handlers.
            group_id (UUID4 | None | NotSet, optional): The group ID to associate
                with the webhook handlers. This allows handlers to be group-scoped
                if their logic requires it. `NOT_SET` indicates that the group context
                is not specified, `None` can mean a system-level or non-group-specific context.
                Defaults to `NOT_SET`.
        """
        self.session = session
        # Store group_id. If NOT_SET, it implies an indeterminate or system-wide context for handlers.
        # Handlers themselves will need to manage this if they require a group_id.
        self.group_id = group_id

    def get_webhook_handler(self, webhook_type_name: str) -> BaseWebhook | None:
        """
        Retrieves a webhook handler instance based on its type name.

        This method dynamically accesses one of the `cached_property` methods
        (e.g., `self.generic`, `self.user`) that correspond to registered
        webhook handler types.

        Args:
            webhook_type_name (str): The name of the webhook handler type
                                     (e.g., "generic", "user"). This should match
                                     the name of a `cached_property` method in this class.

        Returns:
            BaseWebhook | None: An instance of the requested webhook handler
                                (e.g., `GenericWebhook`, `UserWebhook`), or None
                                if no handler with that name is defined.
        """
        # getattr is used to dynamically access properties like self.generic or self.user
        # These properties are cached, so the handler is only instantiated once per AllWebhooks instance.
        if hasattr(self, webhook_type_name):
            handler = getattr(self, webhook_type_name)
            if isinstance(handler, BaseWebhook):  # Ensure it's a valid handler type
                return handler
        return None  # Return None if the handler type name doesn't match a property or isn't a BaseWebhook

    @cached_property
    def generic(self) -> GenericWebhook:
        """
        Provides a cached instance of the `GenericWebhook` handler.
        Instantiated with the session and group_id of this `AllWebhooks` instance.
        """
        # `self.group_id` can be UUID, None, or NOT_SET. `GenericWebhook` needs to handle these.
        # If GenericWebhook expects UUID | None, then NOT_SET should be converted or handled.
        # Assuming GenericWebhook can take `group_id` as `UUID4 | None`.
        effective_group_id = None if self.group_id is NOT_SET else self.group_id
        return GenericWebhook(self.session, group_id=effective_group_id)

    @cached_property
    def user(self) -> UserWebhook:
        """
        Provides a cached instance of the `UserWebhook` handler.
        Instantiated with the session and group_id of this `AllWebhooks` instance.
        """
        effective_group_id = None if self.group_id is NOT_SET else self.group_id
        return UserWebhook(self.session, group_id=effective_group_id)

    # To add more webhook types, define them as classes inheriting from BaseWebhook
    # (like GenericWebhook, UserWebhook) and then add a new cached_property here:
    #
    # @cached_property
    # def another_type(self) -> AnotherWebhookTypeHandler:
    #     return AnotherWebhookTypeHandler(self.session, self.group_id)
    #
    # The `get_webhook_handler` method would then be able to retrieve it by name "another_type".
