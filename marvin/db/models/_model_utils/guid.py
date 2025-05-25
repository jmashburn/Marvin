"""
This module provides a platform-independent GUID (Globally Unique Identifier)
type for SQLAlchemy models.

It defines the `GUID` class, a `TypeDecorator` that uses PostgreSQL's native
UUID type when available, and falls back to a CHAR(32) representation for other
database backends, storing the UUID as a hex string.
"""
import uuid
from typing import Any

from sqlalchemy import Dialect
from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # Renamed to avoid conflict
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """
    Platform-independent GUID type for SQLAlchemy.

    Uses PostgreSQL's native UUID type if the dialect is PostgreSQL.
    Otherwise, it uses CHAR(32) and stores the GUID as a 32-character
    hexadecimal string.
    """

    impl = CHAR
    cache_ok = True

    @staticmethod
    def generate() -> uuid.UUID:
        """
        Generates a new UUID version 4.

        Returns:
            uuid.UUID: A new UUID object.
        """
        return uuid.uuid4()

    @staticmethod
    def convert_value_to_guid(value: Any, dialect: Dialect) -> str | uuid.UUID | None:
        """
        Converts a given value to its appropriate database representation for a GUID.

        - If the dialect is PostgreSQL, the value is returned as a string (PG UUID type handles it).
        - Otherwise, the UUID is converted to a 32-character hex string.
        - If the value is None, None is returned.

        Args:
            value (Any): The value to convert. Can be a `uuid.UUID` instance,
                         a string representation of a UUID, or None.
            dialect (Dialect): The SQLAlchemy dialect in use.

        Returns:
            str | uuid.UUID | None: The database-ready representation of the GUID, or None.
        """
        if value is None:
            return None
        elif dialect.name == "postgresql":
            # PostgreSQL's UUID type can handle UUID objects or string representations
            return value if isinstance(value, uuid.UUID) else str(value)
        else:
            # For other dialects, store as a 32-character hex string
            if not isinstance(value, uuid.UUID):
                # Attempt to convert from string or other compatible type to UUID
                value = uuid.UUID(value)
            return f"{value.int:032x}"

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        """
        Loads the dialect-specific implementation for the GUID type.

        Args:
            dialect (Dialect): The SQLAlchemy dialect.

        Returns:
            Any: The dialect-specific type (PostgreSQL UUID or CHAR(32)).
        """
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Any, dialect: Dialect) -> str | None:
        """
        Processes the value before binding it as a parameter in a SQL query.

        Converts Python `uuid.UUID` objects or string UUIDs into the
        database-specific format (string hex for non-PostgreSQL, or passes
        through for PostgreSQL which handles UUID objects).

        Args:
            value (Any): The value to process.
            dialect (Dialect): The SQLAlchemy dialect.

        Returns:
            str | None: The processed value for the database.
        """
        return self.convert_value_to_guid(value, dialect) # type: ignore

    def _uuid_value(self, value: Any) -> uuid.UUID | None:
        """
        Ensures the given value is a `uuid.UUID` object if not None.

        If the value is already a UUID, it's returned directly.
        If it's a string, it's converted to a UUID.

        Args:
            value (Any): The value to convert (typically a string from the DB).

        Returns:
            uuid.UUID | None: The UUID object, or None.
        """
        if value is None:
            return None
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)  # Converts hex string from DB back to UUID
            return value

    def process_result_value(self, value: Any, dialect: Dialect) -> uuid.UUID | None:
        """
        Processes the value retrieved from the database.

        Converts the database representation (hex string for non-PostgreSQL,
        or native UUID for PostgreSQL) back into a Python `uuid.UUID` object.

        Args:
            value (Any): The value from the database.
            dialect (Dialect): The SQLAlchemy dialect.

        Returns:
            uuid.UUID | None: The Python UUID object.
        """
        return self._uuid_value(value)

    def sort_key_function(self, value: uuid.UUID) -> uuid.UUID | None:
        """
        Provides a sort key for the UUID value.

        Ensures that comparison and sorting operations use actual UUID objects.

        Args:
            value (uuid.UUID): The UUID value.

        Returns:
            uuid.UUID | None: The UUID object itself, for sorting.
        """
        return self._uuid_value(value)
