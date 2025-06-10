"""
This module provides the `HttpRepo` mixin class, designed to encapsulate
common HTTP CRUD (Create, Read, Update, Delete) logic that interacts with
a generic repository.

It standardizes exception handling by converting repository or database errors
into appropriate FastAPI `HTTPException` responses. This mixin is intended
to be used via composition within FastAPI route controller classes.
"""

from collections.abc import Callable  # For typing callables like exception_msgs
from logging import Logger  # For type hinting logger
from typing import Generic, TypeVar  # For creating generic classes and types

import sqlalchemy.exc  # For catching specific SQLAlchemy exceptions
from fastapi import HTTPException, status  # For raising HTTP exceptions
from pydantic import UUID4, BaseModel  # For UUID type and base Pydantic model

# Assuming RepositoryGeneric is defined elsewhere and provides CRUD methods
from marvin.repos.repository_generic import RepositoryGeneric

# Assuming ErrorResponse is a Pydantic model or utility for formatting error details
from marvin.schemas.response import ErrorResponse

# Type variables for Pydantic schemas used in CRUD operations:
C = TypeVar("C", bound=BaseModel)  # Schema for Create operations
R = TypeVar("R", bound=BaseModel)  # Schema for Read operations (response)
U = TypeVar("U", bound=BaseModel)  # Schema for Update operations (input)
# D = TypeVar("D", bound=BaseModel) # Could add a D for Delete response if needed


class HttpRepo(Generic[C, R, U]):
    """
    A mixin class providing standardized HTTP CRUD operations and exception handling.

    This class uses generic types for Pydantic schemas (Create, Read, Update)
    to work with different types of entities. It requires a `RepositoryGeneric`
    instance for data access and a logger.

    Intended usage is via composition within a controller class:
    ```python
    class MyController:
        def __init__(self, repo: RepositoryGeneric, logger: Logger, ...):
            self.crud_helper = HttpRepo(repo, logger, exception_msgs=self.get_custom_error_msg)
            # ...
    ```
    """

    repo: RepositoryGeneric  # Type hint for the repository this mixin operates on
    """The generic repository instance for database operations."""

    exception_msgs: Callable[[type[Exception]], str] | None
    """
    An optional callable that takes an exception type and returns a custom
    user-friendly error message string for that exception type.
    """

    default_message: str = "An unexpected error occurred processing your request."
    """Default error message if a specific one is not found or provided."""

    logger: Logger
    """Logger instance for logging errors and operations."""

    def __init__(
        self,
        repo: RepositoryGeneric,  # Specific type hints for repo based on C, R, U
        logger: Logger,
        exception_msgs: Callable[[type[Exception]], str] | None = None,
        default_message: str | None = None,
    ) -> None:
        """
        Initializes the HttpRepo mixin.

        Args:
            repo (RepositoryGeneric[R, C, U]): The repository instance for data operations.
                The generic types `R`, `C`, `U` should correspond to the Pydantic
                schemas for Read, Create, and Update operations respectively for the
                entity being managed. `Any` is used for the SQLAlchemy Model type as
                it's not directly used by HttpRepo's method signatures beyond the repo.
            logger (Logger): An instance of a logger.
            exception_msgs (Callable[[type[Exception]], str] | None, optional):
                A function that maps exception types to custom error messages.
                Defaults to None.
            default_message (str | None, optional): A custom default error message.
                If None, a standard default message is used. Defaults to None.
        """
        self.repo = repo
        self.logger = logger
        self.exception_msgs = exception_msgs

        if default_message:  # Override default message if provided
            self.default_message = default_message

    def get_exception_message(self, ex: Exception) -> str:
        """
        Gets a user-friendly message for a given exception.

        If `self.exception_msgs` is configured and provides a message for the
        type of `ex`, that message is used. Otherwise, `self.default_message` is returned.

        Args:
            ex (Exception): The exception that occurred.

        Returns:
            str: A user-friendly error message.
        """
        if self.exception_msgs:
            custom_msg = self.exception_msgs(type(ex))
            if custom_msg:  # Ensure the callable returned a non-empty message
                return custom_msg
        return self.default_message

    def handle_exception(self, ex: Exception) -> None:
        """
        Handles exceptions during CRUD operations by logging, rolling back the session,
        and raising an appropriate `HTTPException`.

        Specifically distinguishes `sqlalchemy.exc.NoResultFound` to raise a 404 error,
        otherwise raises a 400 error for other handled exceptions.

        Args:
            ex (Exception): The exception to handle.

        Raises:
            HTTPException: A FastAPI HTTPException (404 or 400) with a formatted error detail.
        """
        # Log the full exception traceback for debugging
        self.logger.exception(ex)
        # Rollback the current database session to prevent inconsistent state
        if hasattr(self.repo, "session") and self.repo.session:
            self.repo.session.rollback()

        # Determine the user-facing error message
        msg = self.get_exception_message(ex)

        # Convert specific SQLAlchemy exceptions to HTTP status codes
        if isinstance(ex, sqlalchemy.exc.NoResultFound):
            # Typically, NoResultFound from repo.get_one would be caught before this,
            # but if repo.update/delete queries and doesn't find, it might raise this.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse.respond(message=msg or "Resource not found.", exception=str(ex)),
            )
        # Add more specific exception type handling here if needed (e.g., IntegrityError for 409)
        else:
            # Default to 400 Bad Request for other handled operational errors
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,  # Or consider 500 for truly unexpected internal errors
                detail=ErrorResponse.respond(message=msg, exception=str(ex)),
            )

    def create_one(self, data: C) -> R:  # Return type R, as create usually returns the created object
        """
        Creates a single new resource.

        Args:
            data (C): The Pydantic schema (Create type) containing data for the new resource.

        Returns:
            R: The Pydantic schema (Read type) of the created resource.

        Raises:
            HTTPException: If creation fails (via `handle_exception`).
        """
        try:
            # Assuming repo.create returns an object that can be validated into schema R
            created_item = self.repo.create(data)
            # item should already be of type R if RepositoryGeneric.create returns self.schema
            return created_item
        except Exception as ex:
            self.handle_exception(ex)
            # handle_exception raises, so this part is effectively unreachable,
            # but linters/compilers might require a return path.
            # Consider re-raising or returning a specific error model if handle_exception didn't raise.
            raise  # Should be unreachable as handle_exception raises

    def get_one(self, item_id: int | str | UUID4, key: str | None = None) -> R:
        """
        Retrieves a single resource by its ID or another unique key.

        Args:
            item_id (int | str | UUID4): The ID or key value of the resource to retrieve.
            key (str | None, optional): The attribute name to use for lookup if not
                                        the primary key. Defaults to None (uses repo's primary key).

        Returns:
            R: The Pydantic schema (Read type) of the retrieved resource.

        Raises:
            HTTPException (404 Not Found): If the resource is not found.
        """
        # Assuming repo.get_one returns an object of type R or None
        item: R | None = self.repo.get_one(item_id, key=key)

        if not item:
            # Standard "Not Found" response
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse.respond(message=f"Resource with ID/key '{item_id}' not found."),
            )
        return item

    def update_one(self, item_id: int | str | UUID4, data: U) -> R:  # item_id first for consistency
        """
        Updates an existing resource.

        First, it verifies the resource exists. Then, attempts the update.

        Args:
            item_id (int | str | UUID4): The ID of the resource to update.
            data (U): The Pydantic schema (Update type) containing data for the update.

        Returns:
            R: The Pydantic schema (Read type) of the updated resource.

        Raises:
            HTTPException (404 Not Found): If the resource to update is not found.
            HTTPException: If the update operation fails (via `handle_exception`).
        """
        # Check if item exists before attempting update (repo.update might do this too)
        # This get_one call ensures a 404 if item doesn't exist.
        # Note: This is an extra DB call. If repo.update handles not found by raising
        # an exception that handle_exception can map to 404, this explicit check could be removed.
        # However, it's safer to ensure the item exists first.
        _ = self.get_one(item_id)  # Ensures item exists, will raise 404 if not.

        try:
            # Assuming repo.update takes ID and data, and returns an object validatable to R
            updated_item = self.repo.update(item_id, data)
            return updated_item
        except Exception as ex:
            self.handle_exception(ex)
            raise  # Unreachable due to handle_exception raising

    def patch_one(self, item_id: int | str | UUID4, data: U) -> R:  # item_id first
        """
        Partially updates an existing resource using a PATCH-like approach.

        Verifies the resource exists, then applies partial updates.
        `data.model_dump(exclude_unset=True, exclude_defaults=True)` is used to get
        only the fields explicitly provided in the patch request.

        Args:
            item_id (int | str | UUID4): The ID of the resource to patch.
            data (U): The Pydantic schema (Update type) containing partial data for the update.
                      Only fields present in `data` will be updated.

        Returns:
            R: The Pydantic schema (Read type) of the patched resource.

        Raises:
            HTTPException (404 Not Found): If the resource to patch is not found.
            HTTPException: If the patch operation fails (via `handle_exception`).
        """
        _ = self.get_one(item_id)  # Ensures item exists, will raise 404 if not.

        try:
            # Prepare data for partial update (only fields that are set)
            patch_data = data.model_dump(exclude_unset=True, exclude_defaults=True)
            if not patch_data:  # If no actual data sent for patching
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=ErrorResponse.respond(message="No fields provided for patch operation."),
                )
            # Assuming repo.patch exists and handles partial updates, or repo.update can differentiate
            # based on exclude_unset=True in model_dump if it receives a dict.
            # If repo.patch is not distinct, this might just call repo.update with partial data.
            # The original had `repo.patch(item_id, patch_data)`, assuming such a method.
            # If `RepositoryGeneric` has a `patch` method:
            # patched_item = self.repo.patch(item_id, patch_data)
            # If not, and `update` handles dicts with partial data:
            patched_item = self.repo.update(item_id, patch_data)  # type: ignore # If update expects full U schema
            return patched_item
        except Exception as ex:
            self.handle_exception(ex)
            raise  # Unreachable

    def delete_one(self, item_id: int | str | UUID4) -> R:  # Return type R for consistency
        """
        Deletes a single resource by its ID.

        Args:
            item_id (int | str | UUID4): The ID of the resource to delete.

        Returns:
            R: The Pydantic schema (Read type) of the resource that was deleted.
               This is useful for returning the deleted object's data in the response.

        Raises:
            HTTPException (404 Not Found): If the resource to delete is not found (checked by repo.delete).
            HTTPException: If deletion fails for other reasons (via `handle_exception`).
        """
        try:
            # Assuming repo.delete finds the item, deletes it, and returns the representation
            # or raises NoResultFound if not found (which handle_exception would turn to 404).
            deleted_item = self.repo.delete(item_id)
            self.logger.info(f"Successfully deleted item with id {item_id}")
            return deleted_item
        except Exception as ex:
            self.handle_exception(ex)
            raise  # Unreachable
