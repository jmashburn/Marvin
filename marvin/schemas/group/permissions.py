"""
This module defines Pydantic schemas related to user permissions within a group
context in the Marvin application.

These schemas are typically used in requests to set or update a user's specific
permissions within a group.
"""

from pydantic import UUID4  # For UUID type validation

from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model for Marvin schemas


class SetPermissions(_MarvinModel):
    """
    Schema for setting or updating a user's permissions within a group.

    This model is likely used as a request body when an administrator or group manager
    assigns specific capabilities to a user within the scope of a particular group.
    The default value for each permission is `False`.
    """

    user_id: UUID4
    """The unique identifier of the user whose permissions are being set."""

    can_manage: bool = False
    """
    Indicates if the user has permission to manage group settings or members.
    Defaults to False.
    """

    can_invite: bool = False
    """
    Indicates if the user has permission to invite other users to the group.
    Defaults to False.
    """

    can_organize: bool = False
    """
    Indicates if the user has permission to organize content or structure within the group
    (e.g., manage categories, tags, or other organizational elements).
    Note: This permission's specific effect depends on its implementation in the application logic.
    Defaults to False.
    """
