"""
This module provides helper functions for asserting user permissions related to
modifying user data within the Marvin application.

These functions are typically used in route handlers to ensure that users
(both admin and non-admin) adhere to defined access control rules when
attempting to update user profiles or permissions.
"""
from fastapi import HTTPException, status # For raising HTTP exceptions
from pydantic import UUID4 # For UUID type validation

# Marvin specific schemas
from marvin.schemas.response.responses import ErrorResponse # Standardized error response
from marvin.schemas.user.user import PrivateUser, UserCreate, UserUpdate # User Pydantic schemas. UserUpdate might be more appropriate for new_data

# List of attribute names that are considered permission-related.
# Used to check if a user is attempting to modify these attributes.
permission_attrs: list[str] = ["can_invite", "can_manage", "can_organize", "admin"]


def _assert_non_admin_user_change_allowed(
    user_id_being_edited: UUID4, current_user: PrivateUser, new_data: UserCreate | UserUpdate
) -> None:
    """
    Asserts that a non-admin user is allowed to make the proposed changes to a user profile.

    Non-admin users can only edit their own profiles. They cannot change their own
    permissions (defined in `permission_attrs`) or their group.

    Args:
        user_id_being_edited (UUID4): The ID of the user profile being edited.
        current_user (PrivateUser): The authenticated user making the request.
        new_data (UserCreate | UserUpdate): The Pydantic schema containing the proposed new data.
                                            (UserUpdate might be more suitable here).

    Raises:
        HTTPException (403 Forbidden): If the non-admin user attempts an unauthorized action,
                                     such as editing another user's profile, changing their
                                     own permissions, or changing their group.
    """
    # Non-admin users can only edit their own profile
    if current_user.id != user_id_being_edited:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=ErrorResponse.respond("Non-admin users can only edit their own profile.")
        )

    # Check if any permission attribute is being changed
    for attr_name in permission_attrs:
        # Ensure both current_user and new_data have the attribute before comparing
        # new_data might be a partial update (UserUpdate), so check existence.
        if hasattr(new_data, attr_name) and \
           getattr(current_user, attr_name, None) != getattr(new_data, attr_name):
            # User is trying to change one of their own permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse.respond("Users are not allowed to change their own permissions."),
            )

    # Check if the user is trying to change their group
    # Assuming `new_data.group` would be the group object or ID.
    # `current_user.group` might be a GroupRead schema or just group_id.
    # This comparison needs to be robust based on actual types.
    # If `new_data.group` refers to the group's name or ID:
    if hasattr(new_data, "group_id") and new_data.group_id is not None and current_user.group_id != new_data.group_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=ErrorResponse.respond("Users do not have permission to change their own group.")
        )
    # If `new_data.group` is a name and `current_user.group` is an object with a name attribute:
    elif hasattr(new_data, "group") and new_data.group is not None and hasattr(current_user, "group") and current_user.group.name != new_data.group:
         # This part of the original logic `current_user.group != new_data.group` is ambiguous.
         # It depends on whether `group` is an ID, a name, or an object.
         # Assuming it refers to group name or ID for this example.
         # A more robust check would compare group IDs if possible.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=ErrorResponse.respond("Users do not have permission to change their own group.")
        )


def assert_user_change_allowed(
    user_id_being_edited: UUID4, current_user: PrivateUser, new_data: UserCreate | UserUpdate
) -> None:
    """
    Asserts that the current user is allowed to make the proposed changes to a user profile.

    This function routes permission checks based on whether the `current_user` is an admin.
    - If not an admin, it calls `_assert_non_admin_user_change_allowed`.
    - If an admin:
        - They cannot edit other users through this specific user-facing endpoint
          (should use dedicated admin APIs).
        - They cannot change their own permissions through this endpoint.

    Args:
        user_id_being_edited (UUID4): The ID of the user profile being edited.
        current_user (PrivateUser): The authenticated user making the request.
        new_data (UserCreate | UserUpdate): Pydantic schema with the proposed new data.
                                            (UserUpdate might be more suitable).

    Raises:
        HTTPException (403 Forbidden): If the proposed change is not allowed.
    """
    if not current_user.admin:
        # Apply rules for non-admin users
        _assert_non_admin_user_change_allowed(user_id_being_edited, current_user, new_data)
        return # If no exception, change is allowed for non-admin

    # current_user is an Admin
    if current_user.id != user_id_being_edited:
        # Admins should use specific admin endpoints to edit other users,
        # not user-facing profile update endpoints. This prevents accidental edits.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=ErrorResponse.respond("Administrators should use the dedicated Admin API to update other users' profiles.")
        )

    # Admin is trying to edit themselves via a user-facing endpoint
    # Check if they are trying to change their own permissions
    for attr_name in permission_attrs:
        if hasattr(new_data, attr_name) and \
           getattr(current_user, attr_name, None) != getattr(new_data, attr_name):
            # Prevent an admin from escalating/changing their own permissions here.
            # Permission changes for admins should ideally be explicit and potentially audited.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=ErrorResponse.respond("Administrators cannot change their own permissions through this endpoint. Use admin tools.")
            )
    
    # Note: Admins might be allowed to change their own group through user-facing endpoints,
    # or this could also be restricted depending on application policy.
    # The original code did not have an explicit group change check for admins editing themselves here.
