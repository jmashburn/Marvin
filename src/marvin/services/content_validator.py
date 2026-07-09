"""Content validation service for schema-driven entries.

This service validates entry content (data_json) against entry type schemas (schema_json).
It ensures that:
- Required fields are present
- Field values match expected types
- Validation constraints are met (min/max, patterns, options, etc.)
"""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from marvin.schemas.platform.entry_type_schema import (
    BooleanFieldSchema,
    DateFieldSchema,
    DateTimeFieldSchema,
    EntryTypeSchemaDefinition,
    FieldSchema,
    JsonFieldSchema,
    MarkdownFieldSchema,
    NumberFieldSchema,
    SelectFieldSchema,
    TextareaFieldSchema,
    TextFieldSchema,
)
from marvin.services import BaseService


class ContentValidationError(ValueError):
    """Raised when entry content fails schema validation."""

    def __init__(self, field_key: str, message: str):
        """Initialize validation error.

        Args:
            field_key: The field that failed validation
            message: Description of the validation failure
        """
        self.field_key = field_key
        self.message = message
        super().__init__(f"Field '{field_key}': {message}")


class ContentValidator(BaseService):
    """Service for validating entry content against entry type schemas."""

    def validate_content(
        self,
        schema_definition: EntryTypeSchemaDefinition,
        data_json: dict[str, Any],
    ) -> None:
        """Validate entry content against schema definition.

        Args:
            schema_definition: The entry type's schema definition
            data_json: The entry's content data to validate

        Raises:
            ContentValidationError: If validation fails
        """
        # Check for required fields
        for field in schema_definition.get_required_fields():
            if field.key not in data_json or data_json[field.key] is None:
                raise ContentValidationError(
                    field.key,
                    "Required field is missing or null",
                )

        # Validate each field present in data_json
        for field_key, field_value in data_json.items():
            field_schema = schema_definition.get_field(field_key)

            # Unknown fields are allowed (for flexibility)
            # They'll be stored but won't be validated against schema
            if field_schema is None:
                self.logger.debug(f"Field '{field_key}' not in schema, allowing as custom field")
                continue

            # Skip validation for null values (unless field is required, checked above)
            if field_value is None:
                continue

            # Validate based on field type
            self._validate_field(field_schema, field_value)

    def _validate_field(self, field_schema: FieldSchema, value: Any) -> None:
        """Validate a single field value against its schema.

        Args:
            field_schema: The field's schema definition
            value: The field value to validate

        Raises:
            ContentValidationError: If validation fails
        """
        field_key = field_schema.key

        # Dispatch to type-specific validator
        if isinstance(field_schema, TextFieldSchema):
            self._validate_text_field(field_schema, value)
        elif isinstance(field_schema, TextareaFieldSchema):
            self._validate_textarea_field(field_schema, value)
        elif isinstance(field_schema, MarkdownFieldSchema):
            self._validate_markdown_field(field_schema, value)
        elif isinstance(field_schema, NumberFieldSchema):
            self._validate_number_field(field_schema, value)
        elif isinstance(field_schema, BooleanFieldSchema):
            self._validate_boolean_field(field_schema, value)
        elif isinstance(field_schema, SelectFieldSchema):
            self._validate_select_field(field_schema, value)
        elif isinstance(field_schema, DateFieldSchema):
            self._validate_date_field(field_schema, value)
        elif isinstance(field_schema, DateTimeFieldSchema):
            self._validate_datetime_field(field_schema, value)
        elif isinstance(field_schema, JsonFieldSchema):
            self._validate_json_field(field_schema, value)
        else:
            # Unknown field type - should not happen with discriminated union
            self.logger.warning(f"Unknown field type for field '{field_key}': {type(field_schema)}")

    def _validate_text_field(self, field_schema: TextFieldSchema, value: Any) -> None:
        """Validate text field."""
        if not isinstance(value, str):
            raise ContentValidationError(
                field_schema.key,
                f"Expected string, got {type(value).__name__}",
            )

        # Check length constraints
        if field_schema.min is not None and len(value) < field_schema.min:
            raise ContentValidationError(
                field_schema.key,
                f"String length {len(value)} is less than minimum {field_schema.min}",
            )

        if field_schema.max is not None and len(value) > field_schema.max:
            raise ContentValidationError(
                field_schema.key,
                f"String length {len(value)} exceeds maximum {field_schema.max}",
            )

        # Check pattern
        if field_schema.pattern is not None:
            try:
                if not re.match(field_schema.pattern, value):
                    raise ContentValidationError(
                        field_schema.key,
                        f"Value does not match pattern: {field_schema.pattern}",
                    )
            except re.error as e:
                raise ContentValidationError(
                    field_schema.key,
                    f"Invalid regex pattern in schema: {e}",
                )

    def _validate_textarea_field(self, field_schema: TextareaFieldSchema, value: Any) -> None:
        """Validate textarea field (same as text field)."""
        if not isinstance(value, str):
            raise ContentValidationError(
                field_schema.key,
                f"Expected string, got {type(value).__name__}",
            )

        # Check length constraints
        if field_schema.min is not None and len(value) < field_schema.min:
            raise ContentValidationError(
                field_schema.key,
                f"String length {len(value)} is less than minimum {field_schema.min}",
            )

        if field_schema.max is not None and len(value) > field_schema.max:
            raise ContentValidationError(
                field_schema.key,
                f"String length {len(value)} exceeds maximum {field_schema.max}",
            )

    def _validate_markdown_field(self, field_schema: MarkdownFieldSchema, value: Any) -> None:
        """Validate markdown field (string type)."""
        if not isinstance(value, str):
            raise ContentValidationError(
                field_schema.key,
                f"Expected string, got {type(value).__name__}",
            )

    def _validate_number_field(self, field_schema: NumberFieldSchema, value: Any) -> None:
        """Validate number field."""
        if not isinstance(value, (int, float)):
            raise ContentValidationError(
                field_schema.key,
                f"Expected number, got {type(value).__name__}",
            )

        # Check range constraints
        if field_schema.min is not None and value < field_schema.min:
            raise ContentValidationError(
                field_schema.key,
                f"Value {value} is less than minimum {field_schema.min}",
            )

        if field_schema.max is not None and value > field_schema.max:
            raise ContentValidationError(
                field_schema.key,
                f"Value {value} exceeds maximum {field_schema.max}",
            )

    def _validate_boolean_field(self, field_schema: BooleanFieldSchema, value: Any) -> None:
        """Validate boolean field."""
        if not isinstance(value, bool):
            raise ContentValidationError(
                field_schema.key,
                f"Expected boolean, got {type(value).__name__}",
            )

    def _validate_select_field(self, field_schema: SelectFieldSchema, value: Any) -> None:
        """Validate select field."""
        if field_schema.multiple:
            # Multiple selection - expect list
            if not isinstance(value, list):
                raise ContentValidationError(
                    field_schema.key,
                    f"Expected list for multiple select, got {type(value).__name__}",
                )

            # Check each value is a valid option
            for item in value:
                if not isinstance(item, str):
                    raise ContentValidationError(
                        field_schema.key,
                        f"Expected string in list, got {type(item).__name__}",
                    )
                if item not in field_schema.options:
                    raise ContentValidationError(
                        field_schema.key,
                        f"Value '{item}' is not a valid option. Valid options: {field_schema.options}",
                    )
        else:
            # Single selection - expect string
            if not isinstance(value, str):
                raise ContentValidationError(
                    field_schema.key,
                    f"Expected string, got {type(value).__name__}",
                )

            if value not in field_schema.options:
                raise ContentValidationError(
                    field_schema.key,
                    f"Value '{value}' is not a valid option. Valid options: {field_schema.options}",
                )

    def _validate_date_field(self, field_schema: DateFieldSchema, value: Any) -> None:
        """Validate date field.

        Accepts ISO 8601 date strings (YYYY-MM-DD) or datetime objects.
        """
        if isinstance(value, datetime):
            return

        if isinstance(value, str):
            # Try parsing as ISO 8601 date
            try:
                datetime.fromisoformat(value.split("T")[0])  # Take date part only
                return
            except ValueError as e:
                raise ContentValidationError(
                    field_schema.key,
                    f"Invalid date format. Expected ISO 8601 (YYYY-MM-DD): {e}",
                )

        raise ContentValidationError(
            field_schema.key,
            f"Expected date string or datetime, got {type(value).__name__}",
        )

    def _validate_datetime_field(self, field_schema: DateTimeFieldSchema, value: Any) -> None:
        """Validate datetime field.

        Accepts ISO 8601 datetime strings or datetime objects.
        """
        if isinstance(value, datetime):
            return

        if isinstance(value, str):
            # Try parsing as ISO 8601 datetime
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return
            except ValueError as e:
                raise ContentValidationError(
                    field_schema.key,
                    f"Invalid datetime format. Expected ISO 8601: {e}",
                )

        raise ContentValidationError(
            field_schema.key,
            f"Expected datetime string or datetime, got {type(value).__name__}",
        )

    def _validate_json_field(self, field_schema: JsonFieldSchema, value: Any) -> None:
        """Validate JSON field.

        Accepts any JSON-serializable value (dict, list, string, number, bool, null).
        No strict type checking - free-form JSON.
        """
        # Any value is valid for JSON field
        # Python dict/list/str/int/float/bool/None all serialize to JSON
        pass


def validate_entry_content(
    schema_definition: EntryTypeSchemaDefinition,
    data_json: dict[str, Any],
) -> None:
    """Helper function to validate entry content.

    Args:
        schema_definition: The entry type's schema definition
        data_json: The entry's content data to validate

    Raises:
        ContentValidationError: If validation fails
    """
    validator = ContentValidator()
    validator.validate_content(schema_definition, data_json)
