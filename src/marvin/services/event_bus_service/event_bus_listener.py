"""
This module defines the base class and concrete implementations for event listeners
within the Marvin application's event bus system.

Event listeners are responsible for:
1. Identifying relevant subscribers (e.g., Apprise URLs, webhook configurations)
   for a given event.
2. Publishing the event data to these subscribers using an appropriate publisher
   (e.g., `ApprisePublisher`, `WebhookPublisher`).

The module includes:
- `EventListenerBase`: An abstract base class defining the event listener interface
  and providing context managers for resource management (DB sessions, repositories).
- `AppriseEventListener`: A listener that finds Apprise URLs subscribed to an event
  and publishes event data to them, potentially enriching URLs with event parameters.
- `WebhookEventListener`: A listener that finds scheduled webhooks relevant to an event
  (specifically `webhook_task` events), potentially processes data based on webhook
  type, and publishes to the webhook URLs.
"""

import contextlib  # For contextmanager decorator
import json  # For serializing event data
from abc import ABC, abstractmethod  # For abstract base classes
from collections.abc import Generator  # For generator type hints
from datetime import UTC, datetime  # For datetime operations
from typing import Any, cast  # For type casting
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit  # For URL manipulation

from fastapi.encoders import jsonable_encoder  # For encoding Pydantic models to JSON-compatible dicts
from pydantic import UUID4  # For UUID type hinting
from sqlalchemy import select  # For SQLAlchemy select statements

# from sqlalchemy import func # `func` was imported but not used
from sqlalchemy.orm.session import Session  # SQLAlchemy session type
from logging import Logger

# Marvin specific imports
from marvin.core import root_logger  # Application logger
from marvin.db.db_setup import session_context  # Context manager for DB sessions
from marvin.db.models.groups.webhooks import GroupWebhooksModel  # , Method # Method enum not directly used here
from marvin.repos.repository_factory import AllRepositories  # Central repository access
from marvin.schemas.group.event import GroupEventNotifierPrivate  # Schema for private notifier details
from marvin.schemas.group.webhook import WebhookRead  # Schema for reading webhook configurations
from marvin.services.webhooks.all_webhooks import AllWebhooks, get_webhooks  # For accessing webhook runners

from .event_types import (  # Core event system types
    Event,
    EventNameSpace,
    EventOperation,
    EventTypes,
    EventWebhookData,
)
from .publisher import ApprisePublisher, PublisherLike, WebhookPublisher  # Publisher implementations


class EventListenerBase(ABC):
    """
    Abstract base class for event listeners.

    Provides a common structure for event listeners, including initialization
    with a group ID and a publisher, and abstract methods for retrieving
    subscribers and publishing to them. It also includes context managers
    for ensuring database sessions and repository access.
    """

    _logger: Logger = root_logger.get_logger("event_bus_listener")
    """A logger instance for service-specific logging."""
    _session: Session | None = None
    """Optional pre-existing SQLAlchemy session."""
    _repos: AllRepositories | None = None
    """Optional pre-existing AllRepositories instance."""
    _webhooks: AllWebhooks | None = None  # Added for WebhookEventListener consistency
    """Optional pre-existing AllWebhooks instance."""

    def __init__(self, group_id: UUID4, publisher: PublisherLike) -> None:
        """
        Initializes the EventListenerBase.

        Args:
            group_id (UUID4): The ID of the group this listener is associated with.
                              Events processed may be scoped to this group.
            publisher (PublisherLike): An instance of a publisher (e.g., ApprisePublisher)
                                       used to send out notifications.
        """
        self.group_id: UUID4 = group_id
        """The group ID this listener is primarily concerned with."""
        self.publisher: PublisherLike = publisher
        """The publisher instance used to dispatch events."""
        # Initialize private attributes for lazy loading of resources
        self._session = None
        self._repos = None
        self._webhooks = None  # Initialize webhooks attribute

    @abstractmethod
    def get_subscribers(self, event: Event) -> list[Any]:  # Return type can vary by implementation
        """
        Abstract method to get a list of all subscribers for a given event.

        Subclasses must implement this to determine who should receive the event
        (e.g., list of Apprise URLs, list of WebhookRead objects).

        Args:
            event (Event): The event for which to find subscribers.

        Returns:
            list[Any]: A list of subscribers. The type of items in the list
                       depends on the concrete listener implementation.
        """
        ...

    @abstractmethod
    def publish_to_subscribers(self, event: Event, subscribers: list[Any]) -> None:  # Param type matches get_subscribers
        """
        Abstract method to publish the given event to all provided subscribers.

        Subclasses must implement this to define how the event is dispatched
        using `self.publisher`.

        Args:
            event (Event): The event to publish.
            subscribers (list[Any]): A list of subscribers (format depends on listener)
                                     to which the event should be published.
        """
        ...

    @contextlib.contextmanager
    def ensure_session(self) -> Generator[Session, None, None]:
        """
        Ensures a SQLAlchemy session is available within a context.

        If `self._session` was provided during construction (e.g., within an existing
        request-response cycle), that session is yielded. Otherwise, a new session
        is created using `session_context` for the duration of the context, and
        it's automatically closed upon exiting.

        This is crucial for listeners that might operate both within a web request
        (session provided) and in background tasks (session needs to be created).

        Yields:
            Generator[Session, None, None]: The active SQLAlchemy session.
        """
        if self._session is None:
            # If no session exists, create one using the session_context manager
            with session_context() as new_session:
                self._session = new_session  # Store for potential reuse within this listener instance
                yield self._session
                self._session = None  # Clear after use if it was temporary
        else:
            # If a session already exists, yield it directly
            yield self._session

    @contextlib.contextmanager
    def ensure_repos(self, group_id: UUID4) -> Generator[AllRepositories, None, None]:
        """
        Ensures an `AllRepositories` instance is available within a context.

        Uses `ensure_session` to get a database session and then provides an
        `AllRepositories` instance initialized with that session and the given `group_id`.
        If `self._repos` was pre-configured, it's used directly.

        Args:
            group_id (UUID4): The group ID to scope the repositories to.

        Yields:
            Generator[AllRepositories, None, None]: The `AllRepositories` instance.
        """
        if self._repos is None:
            # If no repositories instance exists, create one within an ensured session context
            with self.ensure_session() as current_session:
                self._repos = AllRepositories(current_session, group_id=group_id)
                yield self._repos
                self._repos = None  # Clear after use if temporary
        else:
            # If a repositories instance already exists, yield it
            yield self._repos

    @contextlib.contextmanager
    def ensure_webhooks(self, group_id: UUID4) -> Generator[AllWebhooks, None, None]:
        """
        Ensures an `AllWebhooks` instance is available within a context.

        Uses `ensure_session` to get a database session and then provides an
        `AllWebhooks` instance initialized for the given `group_id`.
        If `self._webhooks` was pre-configured, it's used directly.

        Args:
            group_id (UUID4): The group ID for which to get webhook runners.

        Yields:
            Generator[AllWebhooks, None, None]: The `AllWebhooks` instance.
        """
        if self._webhooks is None:
            # If no webhooks instance exists, create one within an ensured session context
            with self.ensure_session() as current_session:
                self._webhooks = get_webhooks(current_session, group_id=group_id)
                yield self._webhooks
                self._webhooks = None  # Clear after use if temporary
        else:
            yield self._webhooks


class AppriseEventListener(EventListenerBase):
    """
    Event listener that publishes events to Apprise-compatible notification services.

    It retrieves configured Apprise URLs for a group that are subscribed to the
    specific event type. It can also update these URLs with event-specific data
    as query parameters for certain Apprise URL schemes (e.g., JSON, XML).
    """

    _option_value_field_name: str = "option"  # Field name on GroupEventNotifierOptionsSummary to get "namespace.slug"

    def __init__(self, group_id: UUID4) -> None:
        """
        Initializes the AppriseEventListener for a specific group.

        Args:
            group_id (UUID4): The ID of the group whose Apprise notifiers will be used.
        """
        super().__init__(group_id, ApprisePublisher())  # Uses ApprisePublisher for dispatching

    def get_subscribers(self, event: Event) -> list[str]:
        """
        Retrieves a list of Apprise URLs subscribed to the given event for the listener's group.

        Filters enabled notifiers and their options to match the event's type.
        Also updates the URLs with event data if applicable (for custom URL schemes).

        Args:
            event (Event): The event to find subscribers for.

        Returns:
            list[str]: A list of processed Apprise URLs ready for notification.
        """
        apprise_urls: list[str] = []
        with self.ensure_repos(self.group_id) as repos:
            # Fetch all enabled group event notifiers (private schema to access apprise_url)
            enabled_notifiers: list[GroupEventNotifierPrivate] = repos.group_event_notifier.multi_query(
                {"enabled": True}, override_schema=GroupEventNotifierPrivate
            )

            # Construct the target event option string (e.g., "core.test-message")
            target_event_option_str = f"{EventNameSpace.namespace.value}.{event.event_type.name.replace('_', '-')}"

            for notifier in enabled_notifiers:
                if not notifier.apprise_url:  # Skip if no URL configured
                    continue
                # Check if any of this notifier's subscribed options match the current event
                for option_summary in notifier.options:
                    if getattr(option_summary, self._option_value_field_name, None) == target_event_option_str:
                        apprise_urls.append(notifier.apprise_url)
                        break  # Found a match for this notifier, no need to check its other options

            # Update URLs with event-specific parameters if applicable
            if apprise_urls:
                apprise_urls = self.update_urls_with_event_data(apprise_urls, event)
        return apprise_urls

    def publish_to_subscribers(self, event: Event, subscribers_apprise_urls: list[str]) -> None:  # Renamed subscribers
        """
        Publishes the event to the provided list of Apprise URLs.

        Args:
            event (Event): The event to publish.
            subscribers_apprise_urls (list[str]): A list of Apprise URLs to send the notification to.
        """
        self.publisher.publish(event, subscribers_apprise_urls)  # Publisher handles the actual sending

    @staticmethod
    def update_urls_with_event_data(apprise_urls: list[str], event: Event) -> list[str]:
        """
        Updates Apprise URLs with event-specific data as query parameters.

        For certain URL schemes (JSON, XML, FORM), it adds event details (like type, ID,
        timestamp, and document_data) as query parameters prefixed with ":". This allows
        Apprise to include this data in the notification payload for those services.

        Args:
            apprise_urls (list[str]): The list of raw Apprise URLs.
            event (Event): The event containing data to be added to URLs.

        Returns:
            list[str]: The list of Apprise URLs, potentially updated with event data.
        """
        # Prepare event data parameters for URL encoding
        event_params = {
            "event_type": event.event_type.name,
            "integration_id": event.integration_id,
            # Serialize document_data to a JSON string for URL parameter
            "document_data": json.dumps(jsonable_encoder(event.document_data)),
            "event_id": str(event.event_id),  # Convert UUID to string
            "timestamp": event.timestamp.isoformat() if event.timestamp else "",  # ISO format or empty string
        }
        # Filter out None values from params, as they shouldn't be in query string
        filtered_event_params = {k: v for k, v in event_params.items() if v is not None}

        processed_urls = []
        for url in apprise_urls:
            if AppriseEventListener.is_custom_data_url_scheme(url):  # Check if URL scheme supports custom data
                # Prepend ":" to keys for Apprise custom key-value pairs via query params
                apprise_custom_params = {f":{k}": v for k, v in filtered_event_params.items()}
                processed_urls.append(AppriseEventListener.merge_query_parameters(url, apprise_custom_params))
            else:
                processed_urls.append(url)  # URL scheme does not support custom data, use as is
        return processed_urls

    @staticmethod
    def merge_query_parameters(url_string: str, params_to_add: dict[str, str]) -> str:  # Renamed params
        """
        Merges additional query parameters into an existing URL string.

        Args:
            url_string (str): The original URL, which may or may not have existing query parameters.
            params_to_add (dict[str, str]): A dictionary of query parameters to add or update.

        Returns:
            str: The new URL string with merged query parameters.
        """
        scheme, netloc, path, query_string, fragment = urlsplit(url_string)
        existing_query_params = parse_qs(query_string)  # Parse existing query string into a dict

        # Update with new parameters. parse_qs values are lists, so ensure new params are also lists for consistency.
        for key, value in params_to_add.items():
            existing_query_params[key] = [value]  # Override or add as a list with one item

        new_query_string = urlencode(existing_query_params, doseq=True)  # Re-encode query parameters
        return urlunsplit((scheme, netloc, path, new_query_string, fragment))  # Reconstruct the URL

    @staticmethod
    def is_custom_data_url_scheme(url_string: str) -> bool:  # Renamed from is_custom_url
        """
        Checks if the given URL string uses a scheme that supports Apprise custom key-value data via query parameters.

        Args:
            url_string (str): The Apprise URL string.

        Returns:
            bool: True if the scheme is one of "form(s)", "json(s)", or "xml(s)"; False otherwise.
        """
        # Ensure URL is a string before splitting
        scheme = str(url_string).split(":", 1)[0].lower()
        # List of Apprise schemes that are known to support custom data via query parameters prefixed with ":"
        return scheme in ["form", "forms", "json", "jsons", "xml", "xmls"]


class WebhookEventListener(EventListenerBase):
    """
    Event listener that handles events by triggering configured group webhooks.

    It specifically listens for `EventTypes.webhook_task` events, which are expected
    to carry `EventWebhookData` detailing a time range. It then finds scheduled
    webhooks within that time range for the group and publishes event data to them.
    It can also invoke registered functions based on `webhook.webhook_type` to generate
    dynamic data for the webhook payload.
    """

    def __init__(self, group_id: UUID4) -> None:
        """
        Initializes the WebhookEventListener for a specific group.

        Args:
            group_id (UUID4): The ID of the group whose webhooks will be processed.
        """
        super().__init__(group_id, WebhookPublisher())  # Uses WebhookPublisher for dispatching

    def get_subscribers(self, event: Event) -> list[WebhookRead]:
        """
        Retrieves a list of scheduled webhooks that match the event criteria.

        This method is interested in `EventTypes.webhook_task` events. For such events,
        it extracts the start and end datetime from `event.document_data` (expected
        to be `EventWebhookData`) and fetches all enabled webhooks for the group
        scheduled within that time range.

        Args:
            event (Event): The event to find subscribers for.

        Returns:
            list[WebhookRead]: A list of `WebhookRead` schemas for webhooks that
                               should be triggered by this event. Returns an empty
                               list if the event is not a relevant webhook task or
                               if no webhooks are scheduled in the given time range.
        """
        # This listener only acts on `webhook_task` events carrying `EventWebhookData`
        if not (event.event_type == EventTypes.webhook_task and isinstance(event.document_data, EventWebhookData)):
            return []  # Not a relevant event for this listener

        # Extract start and end datetime from event data to find matching scheduled webhooks
        webhook_event_data: EventWebhookData = cast(EventWebhookData, event.document_data)
        scheduled_webhooks_list = self.get_scheduled_webhooks(webhook_event_data.webhook_start_dt, webhook_event_data.webhook_end_dt)
        return scheduled_webhooks_list

    def publish_to_subscribers(self, event: Event, subscribers_webhooks: list[WebhookRead]) -> None:  # Renamed subscribers
        """
        Publishes the event data to the provided list of webhook configurations.

        For each webhook, it may dynamically generate data by calling a registered
        function based on `webhook.webhook_type` (if the event operation is 'info').
        The (potentially dynamic) data is then included in the webhook payload.

        Args:
            event (Event): The event containing data to publish. `event.document_data`
                           is expected to be `EventWebhookData`.
            subscribers_webhooks (list[WebhookRead]): A list of `WebhookRead` schemas
                                                      representing the webhooks to trigger.
        """
        # This method returns True in original code but is typed as None. Assuming None is correct.
        # with self.ensure_repos(self.group_id) as repos: # `repos` is not used in this method

        if not isinstance(event.document_data, EventWebhookData):
            self._logger.warning(f"WebhookEventListener received event with mismatched document_data type: {type(event.document_data)}")
            return

        webhook_event_data: EventWebhookData = cast(EventWebhookData, event.document_data)

        for webhook_config in subscribers_webhooks:
            dynamic_payload_data = {}  # Data to be generated by webhook_type specific functions

            # If the event operation is 'info', try to get data from a registered webhook type handler
            if webhook_event_data.operation == EventOperation.info:
                with self.ensure_webhooks(self.group_id) as webhook_runners:  # Get webhook runners
                    # Check if a runner (handler) exists for the webhook's type
                    if webhook_config.webhook_type and hasattr(webhook_runners, webhook_config.webhook_type.name):
                        webhook_type_handler = getattr(webhook_runners, webhook_config.webhook_type.name)
                        if webhook_type_handler and callable(getattr(webhook_type_handler, "info", None)):
                            try:
                                # Call the .info() method of the handler to get dynamic data
                                dynamic_payload_data = webhook_type_handler.info()
                                self._logger.debug(
                                    f"Dynamic data for webhook {webhook_config.name} (type: {webhook_config.webhook_type.name}): {dynamic_payload_data}"
                                )
                            except Exception as e:
                                self._logger.error(
                                    f"Error executing .info() for webhook type {webhook_config.webhook_type.name} on webhook {webhook_config.name}: {e}"
                                )

            # Update the event's document_data with the dynamic payload for this specific webhook
            # This is a bit tricky as it modifies the event's document_data for each subscriber.
            # It might be better to create a copy or pass data directly to publisher.
            # Original: event.document_data.document_type = webhook.webhook_type (Modifies original event)
            # Original: webhook_data.webhook_body = data (Modifies original event's document_data)

            # Create a specific payload for this webhook call
            current_webhook_payload_body = dynamic_payload_data or {}  # Use dynamic data or empty dict

            # The publisher's `publish` method for WebhookPublisher needs to be designed
            # to accept the original event, the target URL, method, and this specific body.
            # Assuming WebhookPublisher.publish can take an additional `body_override` or similar.
            # The original code modified `event.document_data.webhook_body`.
            # A cleaner way is to pass specific data to the publisher for this call.

            # For now, replicating the modification of a shared object, though it's not ideal:
            # Create a mutable copy of the original document data for this specific publish operation
            current_event_document_data = webhook_event_data.model_copy(deep=True)
            current_event_document_data.document_type = webhook_config.webhook_type  # Set specific document type
            current_event_document_data.webhook_body = current_webhook_payload_body  # Set specific body

            # Create a new Event instance or a modified copy for this specific publish call
            # to avoid side effects if event object is reused.
            # This can be complex if Event is deeply nested.
            # Simpler: Publisher's `publish` method should handle constructing the final payload.
            # Let's assume the publisher's `publish` method for WebhookPublisher is smart.
            # It would receive the base `event`, the `webhook_config.url`, `webhook_config.method`,
            # and the `current_webhook_payload_body`.

            # The original code modifies `webhook_data.webhook_body` (which is `event.document_data.webhook_body`)
            # and then calls `self.publisher.publish`. This means `event.document_data` is mutated.
            webhook_event_data.webhook_body = current_webhook_payload_body
            webhook_event_data.document_type = webhook_config.webhook_type  # Also set the document_type for this publish

            if current_webhook_payload_body or webhook_config.method == webhook_config.method.GET:  # Send if data or GET request
                self.publisher.publish(
                    event,  # The (potentially mutated) event
                    [webhook_config.url],  # List containing single URL for this webhook
                    method=webhook_config.method.name,  # HTTP method for this webhook
                )
            else:
                self._logger.info(f"Skipping webhook {webhook_config.name} as no data was generated by its type handler and it's not a GET request.")
        # Original code had `return True` which doesn't match `-> None` type hint.
        # Assuming side effect only, so no explicit return.
        return

    def get_scheduled_webhooks(self, start_datetime: datetime, end_datetime: datetime) -> list[WebhookRead]:  # Renamed params
        """
        Fetches all enabled webhooks for the listener's group that are scheduled
        to run within the specified time window (inclusive of start, exclusive of end for time part).

        The comparison is done on the `scheduled_time` field of the webhooks,
        compared against the time parts of `start_datetime` and `end_datetime` (converted to UTC).

        Args:
            start_datetime (datetime): The start of the time window (inclusive).
            end_datetime (datetime): The end of the time window (exclusive for time part).

        Returns:
            list[WebhookRead]: A list of `WebhookRead` schemas for matching scheduled webhooks.
        """
        with self.ensure_session() as session:
            # Convert start/end datetimes to UTC time objects for comparison
            start_time_utc = start_datetime.astimezone(UTC).time()
            end_time_utc = end_datetime.astimezone(UTC).time()

            # Build the query for fetching scheduled webhooks
            stmt = select(GroupWebhooksModel).where(
                GroupWebhooksModel.enabled == True,  # noqa: E712 - SQLAlchemy specific comparison
                GroupWebhooksModel.scheduled_time >= start_time_utc,  # Compare time part
                GroupWebhooksModel.scheduled_time < end_time_utc,  # Compare time part (exclusive end)
                GroupWebhooksModel.group_id == self.group_id,  # Scope to listener's group
            )
            # Execute query and convert SQLAlchemy models to Pydantic schemas
            db_webhooks = session.execute(stmt).scalars().all()
            return [WebhookRead.model_validate(db_webhook) for db_webhook in db_webhooks]
