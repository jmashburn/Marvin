"""
This module defines Pydantic schemas for managing group-specific webhook
configurations within the Marvin application.

It includes an enumeration for HTTP methods (`WebhookMethod`) and schemas for
creating (`WebhookCreate`), updating (`WebhookUpdate`), reading (`WebhookRead`),
and paginating (`WebhookPagination`) webhook configurations. A custom validator
is provided for parsing `scheduled_time`.
"""

import datetime
import enum  # For creating enumerations
from typing import Any

from isodate import parse_time as isodate_parse_time  # Renamed to avoid conflict with datetime.time.parse
from pydantic import UUID4, ConfigDict, HttpUrl, ValidationInfo, field_validator  # Added ValidationInfo

from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model

# Using the custom datetime_parser from _marvin module
from marvin.schemas._marvin.datetime_parser import parse_datetime as marvin_parse_datetime
from marvin.schemas.response.pagination import PaginationBase  # Base for pagination responses

# Enum for different document types a webhook might be associated with
from marvin.services.event_bus_service.event_types import EventDocumentType


class WebhookMethod(str, enum.Enum):
    """
    Enumeration for HTTP methods supported by webhooks.
    """

    GET = "GET"  # HTTP GET method.
    POST = "POST"  # HTTP POST method.


class WebhookCreate(_MarvinModel):
    """
    Schema for creating a new webhook configuration.
    Includes fields for enabling the webhook, naming it, specifying the target URL,
    HTTP method, type, and an optional scheduled time for execution.
    """

    enabled: bool = True
    """Whether the webhook is active. Defaults to True."""
    name: str
    """A user-defined name for the webhook (e.g., "Notify on Task Completion")."""
    url: HttpUrl
    """The target URL to which the webhook request will be sent. Must be a valid HTTP/HTTPS URL."""
    method: WebhookMethod = WebhookMethod.POST
    """The HTTP method to use for the webhook request. Defaults to POST."""
    webhook_type: EventDocumentType = EventDocumentType.generic
    """
    The type of event or document this webhook is associated with.
    Influences payload or trigger conditions. Defaults to 'generic'.
    """
    scheduled_time: datetime.time
    """
    The time (UTC) at which the webhook is scheduled to run, if it's a scheduled webhook.
    This field is processed by `validate_scheduled_time` to handle various input formats.
    """

    @field_validator("scheduled_time", mode="before")
    @classmethod
    def validate_scheduled_time(cls, v: Any, info: ValidationInfo) -> datetime.time:  # Added info and correct v type
        """
        Validates and parses the `scheduled_time` field from various input types.

        Accepts `datetime.time` objects directly.
        Parses string inputs that represent either:
        1. A full datetime string: It's converted to UTC, and then the time part is extracted.
        2. A time string (parsable by `isodate.parse_time`): It's parsed directly.
           Note: `isodate.parse_time` typically expects ISO 8601 time strings.
                 The original `parse_time` might have been `datetime.time.fromisoformat`
                 or a custom one. Using `isodate_parse_time` as per import.

        Args:
            v (Any): The input value for `scheduled_time`.
            info (ValidationInfo): Pydantic validation info object.

        Returns:
            datetime.time: The parsed time object (naive, representing UTC time).

        Raises:
            ValueError: If the input value cannot be parsed into a valid `datetime.time`.
        """
        if isinstance(v, datetime.time):  # If already a time object, return as is
            return v

        # List of parser functions to try in order
        # First, try parsing as a full datetime string, then convert to UTC time
        # Second, try parsing as a time string using isodate's parse_time
        parser_funcs = [
            lambda x: marvin_parse_datetime(x).astimezone(datetime.UTC).time(),  # Custom datetime parser
            isodate_parse_time,  # isodate for ISO 8601 time strings like "HH:MM:SS"
        ]

        for parser_func in parser_funcs:
            try:
                # Attempt to parse the value using the current parser function
                parsed_value = parser_func(v)
                # Ensure the parsed value is indeed a datetime.time object
                if isinstance(parsed_value, datetime.time):
                    return parsed_value
                # If parser_func returns a datetime object (e.g. marvin_parse_datetime)
                # and we only need time part, this might need adjustment.
                # However, the lambda already extracts .time().
            except (ValueError, TypeError, AttributeError):  # Catch common parsing errors
                continue  # Try next parser if current one fails

        # If all parsers fail, raise a ValueError
        raise ValueError(f"Invalid format for scheduled_time: '{v}'. Expected HH:MM:SS, ISO datetime, or existing time object.")


class WebhookUpdate(WebhookCreate):
    """
    Schema for updating an existing webhook configuration.
    Extends `WebhookCreate`, implying all fields for creation can also be updated.
    It additionally requires `group_id`, though `group_id` is typically immutable
    for an existing resource or handled via URL path.

    NOTE: For partial updates (PATCH), fields should ideally be `Optional`.
    This schema suggests a PUT-style update. The presence of `group_id` here
    might be for internal use or validation during update, but changing a webhook's
    group is an unusual operation.
    """

    group_id: UUID4  # This field might be redundant if group_id is part of the URL path for update.
    """The unique identifier of the group this webhook belongs to."""
    # Inherits fields: enabled, name, url, method, webhook_type, scheduled_time


class WebhookRead(WebhookUpdate):  # Inherits group_id from WebhookUpdate
    """
    Schema for representing a webhook configuration when read from the system.
    Extends `WebhookUpdate` by adding the unique `id` of the webhook.
    """

    id: UUID4
    """The unique identifier of the webhook configuration."""
    # Inherits fields: enabled, name, url, method, webhook_type, scheduled_time, group_id
    model_config = ConfigDict(from_attributes=True)  # Allows creating from ORM model attributes


class WebhookPagination(PaginationBase):
    """
    Schema for paginated responses containing a list of webhook configurations.
    """

    items: list[WebhookRead]
    """The list of webhook configurations for the current page, serialized as `WebhookRead`."""
