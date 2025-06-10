"""
This module defines FastAPI routes for validation purposes within the Marvin application.

It provides public endpoints that can be used to check the availability or uniqueness
of certain identifiers like usernames, email addresses, and group names, often
used for client-side validation before form submissions.
"""
# UUID was imported but not used. slugify was imported but not used.
# from uuid import UUID
# from slugify import slugify

from fastapi import APIRouter, Depends  # Core FastAPI components
from sqlalchemy.orm.session import Session  # SQLAlchemy session type

# Marvin specific imports
from marvin.db.db_setup import generate_session  # Database session generator
from marvin.repos.all_repositories import get_repositories  # Central repository access

# Renamed to avoid conflict with Pydantic's ValidationResponse if it existed.
# Assuming this is a custom schema for validation responses.
from marvin.schemas.response import ValidationResponse as MarvinValidationResponse

# Public router for validation endpoints.
# No prefix is added here; it's expected to be included by a parent router (e.g., /validate).
router = APIRouter(tags=["Utilities - Validators"])


@router.get("/user/name", response_model=MarvinValidationResponse, summary="Validate Username Uniqueness")
def validate_username_uniqueness(name: str, session: Session = Depends(generate_session)) -> MarvinValidationResponse:
    """
    Checks if a username already exists in the system (case-insensitive).

    This endpoint is useful for client-side validation to inform a user if their
    desired username is available before they attempt to register.

    Args:
        name (str): The username to validate.
        session (Session): SQLAlchemy database session, injected by FastAPI.

    Returns:
        MarvinValidationResponse: A Pydantic model indicating if the username is `valid`
                                  (i.e., does not exist and is therefore available).
    """
    # Access repositories without group scoping for system-wide username check
    db = get_repositories(session, group_id=None)
    # Attempt to find an existing user with the given username (case-insensitive)
    existing_user = db.users.get_one(name, key="username", any_case=True)
    # If no user exists with that name, the name is valid (available)
    return MarvinValidationResponse(valid=existing_user is None)


@router.get("/user/email", response_model=MarvinValidationResponse, summary="Validate User Email Uniqueness")
def validate_user_email_uniqueness(email: str, session: Session = Depends(generate_session)) -> MarvinValidationResponse:
    """
    Checks if an email address already exists in the system (case-insensitive).

    Useful for client-side validation during registration to ensure the email
    is not already in use.

    Args:
        email (str): The email address to validate.
        session (Session): SQLAlchemy database session, injected by FastAPI.

    Returns:
        MarvinValidationResponse: A Pydantic model indicating if the email is `valid`
                                  (i.e., does not exist and is therefore available).
    """
    db = get_repositories(session, group_id=None)
    # Attempt to find an existing user with the given email (case-insensitive)
    existing_user = db.users.get_one(email, key="email", any_case=True)
    # If no user exists with that email, the email is valid (available)
    return MarvinValidationResponse(valid=existing_user is None)


@router.get("/group/name", response_model=MarvinValidationResponse, summary="Validate Group Name Uniqueness")  # Changed path for clarity
def validate_group_name_uniqueness(name: str, session: Session = Depends(generate_session)) -> MarvinValidationResponse:
    """
    Checks if a group name already exists in the system.

    Helpful for interfaces where users can create new groups, to ensure the chosen
    name is unique before submission. Group name checks are typically case-sensitive
    or handled by slug uniqueness, depending on repository implementation.
    `db.groups.get_by_name` is assumed to handle the appropriate matching logic.

    Args:
        name (str): The group name to validate.
        session (Session): SQLAlchemy database session, injected by FastAPI.

    Returns:
        MarvinValidationResponse: A Pydantic model indicating if the group name is `valid`
                                  (i.e., does not exist and is therefore available).
    """
    db = get_repositories(session, group_id=None)
    # Attempt to find an existing group with the given name
    existing_group = db.groups.get_by_name(name)
    # If no group exists with that name, the name is valid (available)
    return MarvinValidationResponse(valid=existing_group is None)
