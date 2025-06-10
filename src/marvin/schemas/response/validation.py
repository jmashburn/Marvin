"""
This module defines Pydantic schemas for standardized validation responses
within the Marvin application.

It includes models used to convey the outcome of validation checks, such as
whether a given piece of data (e.g., a username or email) is considered valid
based on certain criteria (e.g., uniqueness).
"""

from pydantic import BaseModel  # Base Pydantic model


class ValidationResponse(BaseModel):
    """
    Schema for a generic validation response.
    Indicates whether a specific validation check passed or failed.
    """

    valid: bool
    """
    A boolean indicating the result of the validation.
    True if the item is valid, False otherwise.
    """
