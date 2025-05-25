"""
This module defines Pydantic schemas and classes related to user authentication
within the Marvin application.

It includes models for representing authentication tokens, data embedded within tokens,
results of operations like unlocking users, and structures for handling credential
submissions via API requests and HTML forms.
"""
from typing import Annotated # For type hinting with FastAPI Form and Pydantic constraints

from fastapi import Form # For defining form data dependencies in FastAPI
from pydantic import UUID4, BaseModel, StringConstraints # Core Pydantic components and constraints

from marvin.schemas._marvin import _MarvinModel # Base Pydantic model for Marvin schemas


class Token(BaseModel): # Can use BaseModel if no _MarvinModel specific features needed
    """
    Schema for representing an access token response.
    Typically returned to the client after successful authentication.
    """
    access_token: str
    """The access token string."""
    token_type: str
    """The type of the token (e.g., "bearer")."""


class TokenData(BaseModel): # Can use BaseModel
    """
    Schema for data embedded within an access token (e.g., JWT payload).
    Contains identifying information about the user.
    """
    user_id: UUID4 | None = None
    """Optional: The unique identifier of the user associated with the token."""
    username: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)] | None = None # type: ignore
    """
    Optional: The username associated with the token.
    The annotation ensures it's processed as lowercase and stripped of whitespace.
    `type: ignore` might be present due to linter issues with complex Annotated types or specific Pydantic versions.
    """


class UnlockResults(_MarvinModel):
    """
    Schema for the response when an operation to unlock user accounts is performed.
    Indicates how many user accounts were successfully unlocked.
    """
    unlocked: int = 0
    """The number of user accounts that were successfully unlocked. Defaults to 0."""


class CredentialsRequest(BaseModel): # Can use BaseModel
    """
    Schema for a generic credentials request, typically used for API-based login
    where data is sent as JSON.
    """
    username: str
    """The username for authentication."""
    password: str
    """The password for authentication."""
    remember_me: bool = False
    """
    Flag indicating if the user wishes to be remembered for a longer session.
    Defaults to False. The actual duration of "remember me" is handled by the auth system.
    """


class CredentialsRequestForm:
    """
    Represents user credentials submitted via an HTML form (e.g., `application/x-www-form-urlencoded`).

    This class uses FastAPI's `Form` dependency to define form fields. It's not a Pydantic
    model itself but is structured to be compatible with FastAPI's form handling.
    Instances of this class will have attributes populated directly from the form data.
    """

    def __init__(
        self,
        username: str = Form(""), # Defines 'username' as a form field, defaulting to empty string.
        password: str = Form(""), # Defines 'password' as a form field.
        remember_me: bool = Form(False), # Defines 'remember_me' as a boolean form field.
    ):
        """
        Initializes with data received from a form submission.

        Args:
            username (str): The username from the form.
            password (str): The password from the form.
            remember_me (bool): The "remember me" flag from the form.
        """
        self.username: str = username
        """The username submitted in the form."""
        self.password: str = password
        """The password submitted in the form."""
        self.remember_me: bool = remember_me
        """The 'remember me' choice from the form."""
