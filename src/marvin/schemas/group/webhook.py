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
from pydantic import UUID4, ConfigDict, HttpUrl, ValidationInfo, field_validator, model_validator  # Added ValidationInfo

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
    scheduled_time: datetime.datetime
    """
    The datetime (UTC) at which the webhook is scheduled to run, if it's a scheduled webhook.
    This field is processed by `validate_scheduled_time` to handle various input formats.
    """

    headers: dict[str, str] | None = None
    """Custom HTTP headers. Values support {{SLUG}} secret interpolation."""

    @field_validator("url", mode="before")
    @classmethod
    def validate_webhook_url(cls, v: Any) -> Any:
        """Block SSRF targets in production. Localhost/private IPs allowed when PRODUCTION=False."""
        from marvin.core.config import get_app_settings
        if get_app_settings().PRODUCTION:
            import ipaddress
            from urllib.parse import urlparse
            url_str = str(v)
            parsed = urlparse(url_str)
            hostname = parsed.hostname or ""
            blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"}
            if hostname in blocked_hosts:
                raise ValueError("Webhook URL cannot target localhost or internal addresses in production")
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local:
                    raise ValueError("Webhook URL cannot target private IP ranges in production")
            except ValueError as e:
                if "cannot target" in str(e):
                    raise
                # Not an IP address — hostname is fine
        return v

    @field_validator("scheduled_time", mode="before")
    @classmethod
    def validate_scheduled_time(cls, v: Any, info: ValidationInfo) -> datetime.datetime:
        """
        Validates and parses the `scheduled_time` field from various input types.

        Accepts `datetime.datetime` objects directly (converts to UTC if timezone-aware).
        Parses string inputs representing datetime values using the custom datetime parser.

        Args:
            v (Any): The input value for `scheduled_time`.
            info (ValidationInfo): Pydantic validation info object.

        Returns:
            datetime.datetime: The parsed datetime object in UTC.

        Raises:
            ValueError: If the input value cannot be parsed into a valid `datetime.datetime`.
        """
        if isinstance(v, datetime.datetime):
            # If already a datetime, ensure it's UTC
            if v.tzinfo is None:
                # Assume naive datetime is UTC
                return v.replace(tzinfo=datetime.UTC)
            return v.astimezone(datetime.UTC)

        # Try parsing as a datetime string
        try:
            parsed_dt = marvin_parse_datetime(v)
            return parsed_dt.astimezone(datetime.UTC)
        except (ValueError, TypeError, AttributeError):
            pass

        # If parsing fails, raise a descriptive error
        raise ValueError(f"Invalid format for scheduled_time: '{v}'. Expected ISO datetime string or datetime object.")


class WebhookSave(WebhookCreate):
    """
    Schema for saving a webhook configuration to the database.
    Extends `WebhookCreate` and is used for creating or updating webhook records.
    It does not include `group_id` as it is typically handled by the URL path in the API.
    """

    group_id: UUID4  # This field might be redundant if group_id is part of the URL path for update.
    """The unique identifier of the group this webhook belongs to."""
    headers_json: dict[str, str] | None = None
    """ORM column name for custom headers. Populated from `headers` by the model validator."""
    model_config = ConfigDict(from_attributes=True)  # Allows creating from ORM model attributes

    @model_validator(mode="after")
    def _sync_headers_to_headers_json(self) -> "WebhookSave":
        """Copy `headers` → `headers_json` so auto_init can find the ORM column name."""
        if self.headers is not None and self.headers_json is None:
            self.headers_json = self.headers
        return self


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
    # Inherits fields: enabled, name, url, method, webhook_type, scheduled_time, group_id, headers
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Bridge headers_json ORM field → headers schema field."""
        if hasattr(obj, "headers_json") and obj.headers_json and not getattr(obj, "headers", None):
            obj.headers = obj.headers_json
        return super().model_validate(obj, **kwargs)


class WebhookPagination(PaginationBase):
    """
    Schema for paginated responses containing a list of webhook configurations.
    """

    items: list[WebhookRead]
    """The list of webhook configurations for the current page, serialized as `WebhookRead`."""


class WebhookExecutionLogRead(_MarvinModel):
    """Schema for reading a webhook execution log entry."""

    id: UUID4
    webhook_id: UUID4
    group_id: UUID4
    executed_at: datetime.datetime
    status: str
    http_status_code: int | None = None
    error_message: str | None = None
    retry_attempt: int = 0
    request_payload: dict | None = None
    response_body: str | None = None

    model_config = ConfigDict(from_attributes=True)
