"""
This module provides convenient aliases for custom database types used in migrations.

It re-exports `datetime` and `GUID` types from their respective model utility
modules. This allows Alembic migration scripts to refer to these custom types
in a simpler way, without needing to import them from deeper module paths.
"""
from marvin.db.models._model_utils.datetime import datetime as _custom_datetime  # Alias to avoid naming conflict
from marvin.db.models._model_utils.guid import GUID as _custom_guid # Alias for clarity

# Re-export for use in Alembic migrations and potentially other database-related operations.
# These aliases provide a stable import path for custom types used in table definitions
# within migration scripts.
DateTime = _custom_datetime
"""Alias for the custom UTC-aware datetime type used in Marvin models."""

GUID = _custom_guid
"""Alias for the custom GUID type used for primary keys in Marvin models."""
