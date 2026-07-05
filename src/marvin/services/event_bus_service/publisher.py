"""
This module defines publisher implementations for the event bus system
within the Marvin application.

Publishers are responsible for taking a processed event and dispatching it
to external services or URLs. It includes:
- `PublisherLike`: A protocol defining the interface for publisher classes.
- `ApprisePublisher`: Publishes events to various notification services using the Apprise library.
- `WebhookPublisher`: Publishes events to specified URLs via HTTP requests (e.g., POST, GET).
"""

import time
from datetime import UTC, datetime
from typing import Any, Protocol  # For defining structural subtyping (interfaces)

import apprise  # Library for sending notifications to many services
import requests  # For making HTTP requests (used by WebhookPublisher)
from fastapi.encoders import jsonable_encoder  # For encoding Pydantic models to JSON

from marvin.core.root_logger import get_logger
from marvin.db.db_setup import session_context
from marvin.db.models.groups.webhook_execution_logs import WebhookExecutionLogModel
from marvin.db.models._model_utils.guid import GUID
from marvin.services.event_bus_service.event_types import Event  # Core Event model

# from marvin.db.models.groups import Method # Method enum was imported but not used directly by string comparison in WebhookPublisher.
# If strict enum usage is desired, this import would be necessary.

# Default timeout for HTTP requests made by WebhookPublisher
DEFAULT_WEBHOOK_TIMEOUT = 15  # seconds

# Retry configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 2  # Exponential: 2^attempt seconds
RETRY_BACKOFF_MAX = 60  # Cap at 60 seconds


class PublisherLike(Protocol):
    """
    A protocol defining the interface for event publisher classes.

    Publishers are responsible for taking an `Event` object and a list of
    target notification URLs (or similar identifiers) and dispatching the
    event information to those targets.
    """

    def publish(self, event: Event, notification_urls: list[str], **kwargs) -> None:  # Added **kwargs for flexibility
        """
        Publishes an event to the specified notification URLs.

        Args:
            event (Event): The event object to publish.
            notification_urls (list[str]): A list of URLs or identifiers for the
                                           notification targets.
            **kwargs: Additional keyword arguments that specific publisher
                      implementations might require (e.g., HTTP method for webhooks).
        """
        ...  # Ellipsis indicates this is a protocol method to be implemented.


class ApprisePublisher:
    """
    Publishes events using the Apprise library to various notification services.

    It initializes an Apprise instance and uses it to send notifications based on
    the event's message content. URLs are tagged with the event ID to help Apprise
    manage notifications, potentially avoiding duplicates if a URL is added multiple times
    for the same event (though Apprise's internal handling of tags is key here).
    """

    def __init__(self, hard_fail: bool = False) -> None:
        """
        Initializes the ApprisePublisher.

        Args:
            hard_fail (bool, optional): If True, an exception will be raised if
                Apprise fails to add a notification URL. Defaults to False.
        """
        # Configure Apprise asset options (e.g., async mode, image handling)
        asset = apprise.AppriseAsset(
            async_mode=True,  # Enable asynchronous notifications if supported by Apprise setup
            image_url_mask="",  # Configuration for image URL masking if needed
        )
        self.apprise = apprise.Apprise(asset=asset)  # Create Apprise instance
        self.hard_fail: bool = hard_fail
        """If True, raise an exception on failure to add an Apprise URL."""

    def publish(self, event: Event, notification_urls: list[str], **_: Any) -> None:  # Added **_ to match protocol
        """
        Publishes an event to a list of notification URLs using Apprise.

        Each notification URL is added to the Apprise instance with a tag derived
        from the event's unique ID. A single `notify` call is then made for all
        tagged URLs.

        Args:
            event (Event): The event object containing message title and body.
            notification_urls (list[str]): A list of Apprise-compatible notification URLs.
            **_ (Any): Catches any additional keyword arguments (ignored by this publisher).
        """
        if not notification_urls:
            return  # No URLs to notify

        tags_for_this_notification: list[str] = []
        for dest_url in notification_urls:
            # Use the event's unique ID as a tag. This helps Apprise identify
            # the notification if the same URL is added multiple times for this event.
            # Apprise typically uses tags to send a notification to all services associated with that tag.
            event_specific_tag = str(event.event_id)
            tags_for_this_notification.append(event_specific_tag)

            # Add the destination URL to Apprise with the event-specific tag
            status = self.apprise.add(dest_url, tag=event_specific_tag)

            if not status and self.hard_fail:
                # If adding the URL fails and hard_fail is True, raise an exception.
                raise Exception(f"Apprise failed to add URL: {dest_url}")

        # Send the notification using the event's message title and body.
        # The `tag` parameter in `notify` ensures that only services matching these tags receive this notification.
        # Using a list of unique tags ensures each URL (if tagged uniquely) gets one notification.
        if tags_for_this_notification:  # Only notify if URLs were successfully added/tagged
            self.apprise.notify(
                title=event.message.title,
                body=event.message.body,
                tag=list(set(tags_for_this_notification)),  # Use unique tags for the notify call
            )


def _log_webhook_execution(
    webhook_id: GUID | None,
    group_id: GUID | None,
    status: str,  # 'success', 'failed', 'retrying'
    http_status_code: int | None = None,
    error_message: str | None = None,
    retry_attempt: int = 0,
) -> None:
    """Log webhook execution to database."""
    if webhook_id is None or group_id is None:
        # Cannot log without IDs
        return

    try:
        with session_context() as session:
            log = WebhookExecutionLogModel(
                session=session,
                webhook_id=webhook_id,
                group_id=group_id,
                executed_at=datetime.now(UTC),
                status=status,
                http_status_code=http_status_code,
                error_message=error_message,
                retry_attempt=retry_attempt,
            )
            session.add(log)
            session.commit()
    except Exception as e:
        logger = get_logger()
        logger.error(f"Failed to log webhook execution: {e}")


def _calculate_retry_delay(attempt: int) -> float:
    """Calculate exponential backoff: 2^attempt seconds, capped at 60."""
    return min(RETRY_BACKOFF_BASE**attempt, RETRY_BACKOFF_MAX)


class WebhookPublisher:
    """
    Publishes events to specified URLs via HTTP requests (webhooks).

    Supports different HTTP methods (GET, POST, PUT, DELETE). For methods that
    carry a body (POST, PUT), the event data is JSON-encoded and sent.
    Includes retry logic with exponential backoff and execution logging.
    """

    def __init__(self, hard_fail: bool = False) -> None:
        """
        Initializes the WebhookPublisher.

        Args:
            hard_fail (bool, optional): If True, an HTTPError will be raised if
                the webhook request returns a 4xx or 5xx status code.
                Defaults to False.
        """
        self.hard_fail: bool = hard_fail
        """If True, raise an exception on HTTP error status codes."""
        self.logger = get_logger()

    def publish(
        self, event: Event, notification_urls: list[str], method: str = "POST", webhook_id: GUID | None = None, group_id: GUID | None = None, **_: Any
    ) -> None:
        """
        Publishes event data to a list of notification URLs using the specified HTTP method.

        Includes retry logic with exponential backoff and logs execution attempts to the database.

        The full `event` object is JSON-encoded and sent as the request body for
        POST and PUT requests. For GET and DELETE, no body is sent.

        Args:
            event (Event): The event object to publish. Its data will be serialized to JSON.
            notification_urls (list[str]): A list of URLs to send the webhook request to.
            method (str, optional): The HTTP method to use (e.g., "POST", "GET", "PUT", "DELETE").
                                    Defaults to "POST".
            webhook_id (GUID | None, optional): The ID of the webhook being executed (for logging).
            group_id (GUID | None, optional): The ID of the group the webhook belongs to (for logging).
            **_ (Any): Catches any additional keyword arguments (ignored by this publisher).


        Raises:
            ValueError: If an unsupported HTTP method is provided.
            requests.exceptions.HTTPError: If `hard_fail` is True and the request
                                           returns an HTTP error status code after retries.
        """
        if not notification_urls:
            return

        # Prepare the event payload for methods that use a body (POST, PUT)
        # `jsonable_encoder` handles Pydantic models, datetimes, UUIDs, etc., correctly for JSON.
        event_payload = jsonable_encoder(event)
        http_method = method.upper()  # Ensure method is uppercase for comparison

        for url in notification_urls:
            # Retry loop for each URL
            for attempt in range(MAX_RETRY_ATTEMPTS):
                try:
                    response: requests.Response | None = None
                    if http_method == "GET":
                        response = requests.get(url, timeout=DEFAULT_WEBHOOK_TIMEOUT)
                    elif http_method == "POST":
                        response = requests.post(url, json=event_payload, timeout=DEFAULT_WEBHOOK_TIMEOUT)
                    elif http_method == "PUT":
                        response = requests.put(url, json=event_payload, timeout=DEFAULT_WEBHOOK_TIMEOUT)
                    elif http_method == "DELETE":
                        response = requests.delete(url, timeout=DEFAULT_WEBHOOK_TIMEOUT)
                    else:
                        raise ValueError(f"Unsupported HTTP method for webhook: {method}")

                    # Check if the request was successful
                    if response is not None:
                        if response.ok:
                            # Success! Log and break out of retry loop
                            _log_webhook_execution(
                                webhook_id=webhook_id,
                                group_id=group_id,
                                status="success",
                                http_status_code=response.status_code,
                                retry_attempt=attempt,
                            )
                            break  # Exit retry loop on success
                        else:
                            # Non-200 status code
                            raise requests.exceptions.HTTPError(f"HTTP {response.status_code}", response=response)

                except (requests.exceptions.RequestException, ValueError) as e:
                    is_last_attempt = attempt == MAX_RETRY_ATTEMPTS - 1

                    # Log the execution attempt
                    _log_webhook_execution(
                        webhook_id=webhook_id,
                        group_id=group_id,
                        status="failed" if is_last_attempt else "retrying",
                        http_status_code=getattr(getattr(e, "response", None), "status_code", None),
                        error_message=str(e),
                        retry_attempt=attempt,
                    )

                    if is_last_attempt:
                        # Final attempt failed
                        self.logger.error(f"Webhook to {url} failed after {MAX_RETRY_ATTEMPTS} attempts: {e}")
                        if self.hard_fail:
                            raise
                        # Don't retry further, move to next URL
                        break
                    else:
                        # Calculate backoff delay and retry
                        delay = _calculate_retry_delay(attempt)
                        self.logger.warning(f"Webhook to {url} failed (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}). Retrying in {delay}s: {e}")
                        time.sleep(delay)
