"""
This module defines publisher implementations for the event bus system
within the Marvin application.

Publishers are responsible for taking a processed event and dispatching it
to external services or URLs. It includes:
- `PublisherLike`: A protocol defining the interface for publisher classes.
- `ApprisePublisher`: Publishes events to various notification services using the Apprise library.
- `WebhookPublisher`: Publishes events to specified URLs via HTTP requests (e.g., POST, GET).
"""
from typing import Protocol # For defining structural subtyping (interfaces)

import apprise # Library for sending notifications to many services
import requests # For making HTTP requests (used by WebhookPublisher)
from fastapi.encoders import jsonable_encoder # For encoding Pydantic models to JSON

from marvin.services.event_bus_service.event_types import Event # Core Event model
# from marvin.db.models.groups import Method # Method enum was imported but not used directly by string comparison in WebhookPublisher.
                                          # If strict enum usage is desired, this import would be necessary.

# Default timeout for HTTP requests made by WebhookPublisher
DEFAULT_WEBHOOK_TIMEOUT = 15 # seconds


class PublisherLike(Protocol):
    """
    A protocol defining the interface for event publisher classes.

    Publishers are responsible for taking an `Event` object and a list of
    target notification URLs (or similar identifiers) and dispatching the
    event information to those targets.
    """
    def publish(self, event: Event, notification_urls: list[str], **kwargs) -> None: # Added **kwargs for flexibility
        """
        Publishes an event to the specified notification URLs.

        Args:
            event (Event): The event object to publish.
            notification_urls (list[str]): A list of URLs or identifiers for the
                                           notification targets.
            **kwargs: Additional keyword arguments that specific publisher
                      implementations might require (e.g., HTTP method for webhooks).
        """
        ... # Ellipsis indicates this is a protocol method to be implemented.


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
            async_mode=True, # Enable asynchronous notifications if supported by Apprise setup
            image_url_mask="", # Configuration for image URL masking if needed
        )
        self.apprise = apprise.Apprise(asset=asset) # Create Apprise instance
        self.hard_fail: bool = hard_fail
        """If True, raise an exception on failure to add an Apprise URL."""

    def publish(self, event: Event, notification_urls: list[str], **_: Any) -> None: # Added **_ to match protocol
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
            return # No URLs to notify

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
        if tags_for_this_notification: # Only notify if URLs were successfully added/tagged
            self.apprise.notify(
                title=event.message.title, 
                body=event.message.body, 
                tag=list(set(tags_for_this_notification)) # Use unique tags for the notify call
            )


class WebhookPublisher:
    """
    Publishes events to specified URLs via HTTP requests (webhooks).

    Supports different HTTP methods (GET, POST, PUT, DELETE). For methods that
    carry a body (POST, PUT), the event data is JSON-encoded and sent.
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

    def publish(self, event: Event, notification_urls: list[str], method: str = "POST", **_: Any) -> None: # Added **_
        """
        Publishes event data to a list of notification URLs using the specified HTTP method.

        The full `event` object is JSON-encoded and sent as the request body for
        POST and PUT requests. For GET and DELETE, no body is sent.

        Args:
            event (Event): The event object to publish. Its data will be serialized to JSON.
            notification_urls (list[str]): A list of URLs to send the webhook request to.
            method (str, optional): The HTTP method to use (e.g., "POST", "GET", "PUT", "DELETE").
                                    Defaults to "POST".
            **_ (Any): Catches any additional keyword arguments (ignored by this publisher).


        Raises:
            ValueError: If an unsupported HTTP method is provided.
            requests.exceptions.HTTPError: If `hard_fail` is True and the request
                                           returns an HTTP error status code.
        """
        if not notification_urls:
            return

        # Prepare the event payload for methods that use a body (POST, PUT)
        # `jsonable_encoder` handles Pydantic models, datetimes, UUIDs, etc., correctly for JSON.
        event_payload = jsonable_encoder(event) 
        http_method = method.upper() # Ensure method is uppercase for comparison

        for url in notification_urls:
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
                    # Log or handle unsupported method if not raising immediately
                    # For now, raising ValueError as per original logic.
                    raise ValueError(f"Unsupported HTTP method for webhook: {method}")

                if self.hard_fail and response is not None:
                    response.raise_for_status() # Raises HTTPError for 4xx/5xx responses
                
                # Optional: Log success/failure based on response status code here if not hard_fail
                # e.g., if response and not response.ok: self.logger.error(...)

            except requests.exceptions.RequestException as e:
                # Handle network errors, timeouts, etc.
                # Log this error. If hard_fail is True, this exception might be re-raised
                # or a custom one raised. For now, it's caught and loop continues unless hard_fail was for status codes only.
                # To make hard_fail apply to RequestException too, re-raise here.
                # self.logger.error(f"Webhook request to {url} failed: {e}")
                if self.hard_fail:
                    raise # Re-raise the requests exception if hard_fail is True
            except ValueError as e: # Catch the unsupported method error
                # self.logger.error(str(e))
                if self.hard_fail:
                    raise
                # If not hard_fail, this error for one URL won't stop others unless re-raised.
                # Depending on desired behavior, might log and continue or propagate.
                # For now, if hard_fail is False, it effectively skips this URL.
                pass # Or log and continue
