"""
This module defines Pydantic schemas used for debugging-related responses
within the Marvin application, typically for administrative debugging endpoints.
"""
from marvin.schemas._marvin import _MarvinModel # Base Pydantic model for Marvin schemas


class DebugResponse(_MarvinModel):
    """
    Schema for a standardized response from debugging endpoints.

    Indicates the success status of a debug operation and provides an optional
    response message or data string.
    """
    success: bool # True if the debug operation was successful, False otherwise.
    response: str | None = None # An optional string containing details, results, or error messages from the debug operation.
