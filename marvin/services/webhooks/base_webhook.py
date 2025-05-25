"""
This module defines the `BaseWebhook` class, an abstract base for creating
specific webhook runner or handler implementations within the Marvin application.

Webhook runners are responsible for processing webhook events of a particular type,
often by fetching relevant data or performing actions based on the event.
"""
from typing import Any # For **kwargs in method signatures
from pydantic import UUID4 # For UUID type hinting
from sqlalchemy.orm import Session # For type hinting SQLAlchemy Session

# `NOT_SET` and `NotSet` were imported but not used in this file.
# from ...repos._utils import NOT_SET, NotSet 


class BaseWebhook:
    """
    Abstract base class for specific webhook runner/handler implementations.

    This class provides a common structure for webhook handlers, including
    initialization with a database session and an optional group ID.
    Subclasses are expected to implement methods for specific actions related
    to their webhook type (e.g., fetching informational data, handling creation,
    updates, or deletions triggered or related to the webhook's purpose).

    The original class docstring mentioned "data access layer" and "AccessModel",
    which might be a misnomer if this class is intended for webhook *processing logic*
    rather than direct database table access (which repositories handle). Assuming
    this is for webhook *type handlers* or *runners*.
    """

    session: Session
    """The SQLAlchemy session, providing database access if needed by the handler."""
    _group_id: UUID4 | None = None
    """
    Internal storage for the group ID. If set, operations might be scoped
    to this group.
    """

    def __init__(self, session: Session, group_id: UUID4 | None = None) -> None:
        """
        Initializes the BaseWebhook handler.

        Args:
            session (Session): The SQLAlchemy database session.
            group_id (UUID4 | None, optional): The unique identifier of the group
                this webhook handler might be scoped to. Defaults to None (no specific group scope).
        """
        self.session = session
        self._group_id = group_id

    @property
    def group_id(self) -> UUID4 | None:
        """
        The group ID this webhook handler is associated with, if any.
        """
        return self._group_id

    def info(self) -> Any: # Return type changed from str to Any for flexibility
        """
        Retrieves informational data relevant to this webhook type.

        This method should be implemented by subclasses to return data that might be
        included in a webhook payload when an 'info' operation is triggered for
        this webhook type (e.g., by `WebhookEventListener`).

        Returns:
            Any: Data specific to the webhook type for an informational event.
                 The structure of the returned data is defined by the subclass.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        # Example: A subclass might return a dictionary of current stats or settings.
        raise NotImplementedError("Subclasses must implement the 'info' method.")

    def create(self, **kwargs: Any) -> Any: # Return type changed to Any
        """
        Handles a 'create' event or operation related to this webhook type.

        Subclasses should implement this to perform actions when a creation event
        relevant to this webhook is processed. The `**kwargs` can carry data
        for the creation.

        Args:
            **kwargs (Any): Arbitrary keyword arguments related to the creation event.

        Returns:
            Any: Result of the creation operation, if applicable.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        # Example: A subclass might create a resource based on kwargs and return its ID or representation.
        raise NotImplementedError("Subclasses must implement the 'create' method.")

    def update(self, **kwargs: Any) -> Any: # Return type changed to Any
        """
        Handles an 'update' event or operation related to this webhook type.

        Subclasses should implement this to perform actions when an update event
        relevant to this webhook is processed.

        Args:
            **kwargs (Any): Arbitrary keyword arguments related to the update event,
                            often including an identifier for the resource to update
                            and the new data.
        Returns:
            Any: Result of the update operation, if applicable.

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the 'update' method.")

    def delete(self, **kwargs: Any) -> Any: # Return type changed to Any
        """
        Handles a 'delete' event or operation related to this webhook type.

        Subclasses should implement this to perform actions when a deletion event
        relevant to this webhook is processed.

        Args:
            **kwargs (Any): Arbitrary keyword arguments related to the deletion event,
                            often including an identifier for the resource to delete.
        Returns:
            Any: Result of the deletion operation, if applicable (e.g., confirmation).

        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the 'delete' method.")
