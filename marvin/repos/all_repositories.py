"""
This module provides a factory function for accessing all application repositories.

It simplifies the creation of an `AllRepositories` instance, which serves as a
central point of access for all data repositories within the Marvin application.
"""

from pydantic import UUID4  # Used for type hinting UUIDs
from sqlalchemy.orm import Session

from ._utils import NOT_SET, NotSet  # Sentinel for unset parameters
from .repository_factory import AllRepositories  # The factory class being instantiated


def get_repositories(session: Session, *, group_id: UUID4 | None | NotSet = NOT_SET) -> AllRepositories:
    """
    Factory function to get an instance of `AllRepositories`.

    `AllRepositories` acts as a centralized access point for all data repositories
    (e.g., users repository, groups repository). This function abstracts its
    instantiation.

    Args:
        session (Session): The SQLAlchemy session to be used by the repositories.
        group_id (UUID4 | None | NotSet, optional): The ID of the group to scope
            the repositories to. This is a keyword-only argument.
            - If a `UUID4` is provided, repositories will be scoped to this group.
            - If `None` is provided, repositories may operate without a group scope
              or on all groups, depending on their implementation (e.g., for admin users).
            - If `NOT_SET` (the default), the `group_id` is considered not provided,
              and the `AllRepositories` instance (and underlying repositories) will
              decide on the default scoping behavior, which might be no specific group
              or a system-default group. This is distinct from explicitly passing `None`.
            Defaults to `NOT_SET`.

    Returns:
        AllRepositories: An instance of the `AllRepositories` class, providing
                         access to various data repositories.
    """
    return AllRepositories(session, group_id=group_id)
