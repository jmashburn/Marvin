"""
This module provides a custom SQLAlchemy `TypeDecorator` for Pydantic's `HttpUrl` type.

It defines `HttpUrlType`, which allows `HttpUrl` objects to be stored as strings
in the database and properly converted back to `HttpUrl` objects when retrieved.
This ensures that URL validation and serialization are handled correctly when
interacting with the database.
"""
from pydantic import HttpUrl
from sqlalchemy.types import Dialect, String, TypeDecorator


class HttpUrlType(TypeDecorator[HttpUrl]):
    """
    Custom SQLAlchemy type for handling Pydantic's `HttpUrl`.

    This type decorator stores `HttpUrl` objects as strings in the database
    and ensures they are parsed back as `HttpUrl` upon retrieval, leveraging
    Pydantic's validation.
    """

    impl = String
    """The underlying SQLAlchemy type used for storage (String)."""

    cache_ok = True
    """Indicates that this TypeDecorator is cacheable."""

    python_type = HttpUrl
    """The Python type this decorator handles."""

    def process_bind_param(self, value: HttpUrl | None, dialect: Dialect) -> str | None:
        """
        Processes the `HttpUrl` value before binding it to a database parameter.

        Converts the `HttpUrl` object to its string representation.

        Args:
            value (HttpUrl | None): The `HttpUrl` object or None.
            dialect (Dialect): The SQLAlchemy dialect being used.

        Returns:
            str | None: The string representation of the URL, or None.
        """
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: str | None, dialect: Dialect) -> HttpUrl | None:
        """
        Processes the string value retrieved from the database.

        Converts the string back into a Pydantic `HttpUrl` object.
        If the value is None or conversion fails (though Pydantic will raise errors),
        it might return None or let the error propagate.

        Args:
            value (str | None): The string value from the database.
            dialect (Dialect): The SQLAlchemy dialect being used.

        Returns:
            HttpUrl | None: The `HttpUrl` object, or None.
        """
        if value is None:
            return None
        # Pydantic's HttpUrl will validate the string upon instantiation
        return HttpUrl(value)
