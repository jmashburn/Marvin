"""
This module provides a factory function for accessing all webhook runner types
within the Marvin application.

It simplifies the creation of an `AllWebhooks` instance, which serves as a
central point of access or a registry for different webhook processing logics
based on webhook types.
"""

from pydantic import UUID4  # For type hinting UUIDs
from sqlalchemy.orm import Session  # For type hinting SQLAlchemy Session

# Utility for handling optionally set parameters
from ...repos._utils import NOT_SET, NotSet  # Sentinel for unset group_id

# The factory class being instantiated, providing access to various webhook runners
from .webhook_factory import AllWebhooks


def get_webhooks(session: Session, *, group_id: UUID4 | None | NotSet = NOT_SET) -> AllWebhooks:
    """
    Factory function to get an instance of `AllWebhooks`.

    `AllWebhooks` acts as a centralized access point or registry for different
    webhook runners or handlers, categorized by webhook type. This function
    abstracts its instantiation and allows for potential scoping by `group_id`
    if webhook runners need group-specific context or data.

    Args:
        session (Session): The SQLAlchemy session, potentially to be used by
                           webhook runners if they need database access.
        group_id (UUID4 | None | NotSet, optional): The ID of the group to scope
            the webhook runners to. This is a keyword-only argument.
            - If a `UUID4` is provided, runners might be scoped to this group.
            - If `None` is provided, runners may operate without a group scope or
              access data across all groups (e.g., for system-level webhooks or admin users).
            - If `NOT_SET` (the default), the `group_id` is considered not provided.
              The `AllWebhooks` instance (and underlying runners) will decide on
              default scoping, which might be no specific group or a system default.
            Defaults to `NOT_SET`.

    Returns:
        AllWebhooks: An instance of the `AllWebhooks` class.
    """
    # Instantiate and return AllWebhooks, passing the session and group_id
    return AllWebhooks(session, group_id=group_id)
