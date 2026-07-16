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
from marvin.core.root_logger import get_logger  # Application logger
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

    _logger: Logger | None = None

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

    @property
    def logger(self) -> Logger:
        """
        Provides access to the Marvin application logger.

        Initializes the logger on first access.
        """
        if not self._logger:
            self._logger = get_logger("event_bus_listener")
        return self._logger

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
        # This listener only acts on events that are not `webhook_task`
        if event.event_type == EventTypes.webhook_task:
            return []

        apprise_urls: list[str] = []
        with self.ensure_repos(self.group_id) as repos:
            # Fetch all enabled group event notifiers (private schema to access apprise_url)
            enabled_notifiers: list[GroupEventNotifierPrivate] = repos.group_event_notifier.multi_query(
                {"enabled": True}, override_schema=GroupEventNotifierPrivate
            )

            # Construct the target event option string (e.g., "core.test_message")
            target_event_option_str = f"{EventNameSpace.namespace.value}.{event.event_type.name.replace('-', '_')}"
            self.logger.debug(f"Target Event {target_event_option_str}")

            for notifier in enabled_notifiers:
                if not notifier.apprise_url:  # Skip if no URL configured
                    continue
                # Check if any of this notifier's subscribed options match the current event
                for option_summary in notifier.options:
                    if getattr(option_summary, self._option_value_field_name, None) == target_event_option_str:
                        self.logger.debug(f"Appending {notifier.apprise_url}")
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


def _resolve_webhook_headers(webhook_config: "WebhookRead", group_id) -> dict[str, str] | None:
    """Resolve {{SLUG}} references in webhook headers using the configured secret backend."""
    raw = getattr(webhook_config, "headers", None) or getattr(webhook_config, "headers_json", None)
    if not raw:
        return None
    from marvin.services.secrets.resolver import resolve_dict
    return resolve_dict(raw, group_id)


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
        Retrieves a list of webhooks that should receive this event.

        This method handles two types of webhook triggers:
        1. Scheduled webhooks (`EventTypes.webhook_task`) - time-based triggers
        2. Event-subscribed webhooks - webhooks that subscribe to specific event types

        Args:
            event (Event): The event to find subscribers for.

        Returns:
            list[WebhookRead]: A list of `WebhookRead` schemas for webhooks that
                               should be triggered by this event.
        """
        # EXISTING: Handle scheduled webhook_task events
        if event.event_type == EventTypes.webhook_task and isinstance(event.document_data, EventWebhookData):
            webhook_event_data: EventWebhookData = cast(EventWebhookData, event.document_data)
            scheduled_webhooks_list = self.get_scheduled_webhooks(webhook_event_data.webhook_start_dt, webhook_event_data.webhook_end_dt)
            return scheduled_webhooks_list

        # NEW: Handle event-subscribed webhooks
        # Find webhooks that have subscribed to this specific event type
        with self.ensure_session() as session:
            stmt = select(GroupWebhooksModel).where(
                GroupWebhooksModel.enabled == True,  # noqa: E712 - SQLAlchemy specific comparison
                GroupWebhooksModel.group_id == self.group_id,
            )
            db_webhooks = session.execute(stmt).scalars().all()

            # Filter to event_driven webhooks whose subscribed_events include this event type
            filtered_webhooks = [
                wh for wh in db_webhooks
                if wh.subscribed_events
                and event.event_type.name in wh.subscribed_events
                and getattr(wh.webhook_type, "value", None) == "event_driven"
            ]

            return [WebhookRead.model_validate(wh) for wh in filtered_webhooks]

    def publish_to_subscribers(self, event: Event, subscribers_webhooks: list[WebhookRead]) -> None:
        """Publish event data to each webhook subscriber."""
        from marvin.services.webhooks.substitution import apply_substitutions

        if event.event_type != EventTypes.webhook_task:
            # Event-driven path: send a clean event envelope
            for webhook_config in subscribers_webhooks:
                resolved_headers = _resolve_webhook_headers(webhook_config, self.group_id)
                payload: dict = {
                    "event_type": event.event_type.name,
                    "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                    "data": jsonable_encoder(event.document_data, exclude_none=True) if event.document_data else {},
                }
                if webhook_config.custom_payload:
                    ctx = {
                        "trigger": event.event_type.name,
                        "timestamp": event.timestamp.isoformat() if event.timestamp else "",
                    }
                    payload["meta"] = apply_substitutions(
                        webhook_config.custom_payload, self.group_id, ctx
                    )
                self.publisher.publish(
                    event,
                    [webhook_config.url],
                    method=webhook_config.method.name,
                    webhook_id=webhook_config.id,
                    group_id=self.group_id,
                    headers=resolved_headers,
                    payload_override=payload,
                )
            return

        # Scheduled webhook_task path
        if not isinstance(event.document_data, EventWebhookData):
            self.logger.warning(
                f"WebhookEventListener: unexpected document_data type: {type(event.document_data)}"
            )
            return

        webhook_event_data: EventWebhookData = cast(EventWebhookData, event.document_data)
        now_iso = datetime.now(UTC).isoformat()

        # Build substitution context once — used by all webhooks in this batch
        workspace_name = ""
        workspace_slug = ""
        try:
            with self.ensure_repos(self.group_id) as repos:
                group = repos.groups.get_one(self.group_id)
                if group:
                    workspace_name = getattr(group, "name", "") or ""
                    workspace_slug = getattr(group, "slug", "") or ""
        except Exception:
            pass

        context = {
            "timestamp": now_iso,
            "workspace_name": workspace_name,
            "workspace_slug": workspace_slug,
            "trigger": "scheduled",
        }

        for webhook_config in subscribers_webhooks:

            handler_data: dict = {}
            webhook_type_name = webhook_config.webhook_type.value if webhook_config.webhook_type else "generic"

            if webhook_event_data.operation == EventOperation.info:
                with self.ensure_webhooks(self.group_id) as webhook_runners:
                    handler = webhook_runners.get_webhook_handler(webhook_type_name)
                    if handler:
                        try:
                            handler_data = handler.info(webhook_config, context)
                        except Exception as e:
                            self.logger.error(
                                f"Error calling .info() for webhook {webhook_config.name} "
                                f"(type={webhook_type_name}): {e}"
                            )

            clean_payload: dict = {
                "type": webhook_type_name,
                "data": handler_data,
            }
            if webhook_config.custom_payload:
                clean_payload["meta"] = apply_substitutions(
                    webhook_config.custom_payload, self.group_id, context
                )

            resolved_headers = _resolve_webhook_headers(webhook_config, self.group_id)
            self.publisher.publish(
                event,
                [webhook_config.url],
                method=webhook_config.method.name,
                webhook_id=webhook_config.id,
                group_id=self.group_id,
                headers=resolved_headers,
                payload_override=clean_payload,
            )

    def get_scheduled_webhooks(self, start_datetime: datetime, end_datetime: datetime) -> list[WebhookRead]:  # Renamed params
        """
        Fetches all enabled webhooks for the listener's group that are scheduled
        to run within the specified datetime window (inclusive of start, exclusive of end).

        The comparison is done on the `scheduled_time` field of the webhooks,
        compared against the full datetime values (converted to UTC).

        Args:
            start_datetime (datetime): The start of the datetime window (inclusive).
            end_datetime (datetime): The end of the datetime window (exclusive).

        Returns:
            list[WebhookRead]: A list of `WebhookRead` schemas for matching scheduled webhooks.
        """
        with self.ensure_session() as session:
            # Convert start/end datetimes to UTC for comparison with stored datetime values
            # Build the query for fetching scheduled webhooks

            stmt = select(GroupWebhooksModel).where(
                GroupWebhooksModel.enabled == True,  # noqa: E712 - SQLAlchemy specific comparison
                GroupWebhooksModel.scheduled_time >= start_datetime.astimezone(UTC),  # Compare full datetime (inclusive)
                GroupWebhooksModel.scheduled_time < end_datetime.astimezone(UTC),  # Compare full datetime (exclusive end)
                GroupWebhooksModel.group_id == self.group_id,  # Scope to listener's group
            )
            # Execute query and convert SQLAlchemy models to Pydantic schemas
            db_webhooks = session.execute(stmt).scalars().all()
            return [WebhookRead.model_validate(db_webhook) for db_webhook in db_webhooks]


class ScheduledTaskListener(EventListenerBase):
    """
    Event listener that executes scheduled tasks when triggered.

    This listener responds to scheduled_task.triggered events by:
    1. Looking up the appropriate handler via TaskHandlerRegistry
    2. Executing the handler with the task configuration
    3. Logging execution results
    4. Emitting completion/failure events
    5. Updating task execution state
    """

    def __init__(self, group_id: UUID4) -> None:
        """
        Initializes the ScheduledTaskListener for a specific group.

        Args:
            group_id (UUID4): The ID of the group this listener is associated with.
        """
        from .publisher import ConsolePublisher  # We don't actually publish anything, but need a publisher

        super().__init__(group_id, ConsolePublisher())

    def get_subscribers(self, event: Event) -> list[str]:
        """
        Returns a list indicating this listener should handle the event.

        Only subscribes to scheduled_task.triggered events.

        Args:
            event (Event): The event to check.

        Returns:
            list[str]: Returns ["scheduled_task_handler"] if this is a triggered event, else empty list.
        """
        if event.event_type == EventTypes.scheduled_task_triggered:
            return ["scheduled_task_handler"]
        return []

    def publish_to_subscribers(self, event: Event, subscribers: list[str]) -> None:
        """
        Executes the scheduled task.

        Args:
            event (Event): The triggered event containing task data.
            subscribers (list[str]): List of subscribers (always ["scheduled_task_handler"]).
        """
        import traceback

        from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel
        from marvin.services.scheduled_tasks import TaskHandlerRegistry

        # Extract task data from event
        if not event.document_data:
            self.logger.error("ScheduledTaskListener: No document_data in event")
            return

        task_id = getattr(event.document_data, "task_id", None)
        if not task_id:
            self.logger.error("ScheduledTaskListener: No task_id in document_data")
            return

        # Load the task from database
        with self.ensure_repos(self.group_id) as repos:
            task = repos.session.get(ScheduledTaskModel, task_id)
            if not task:
                self.logger.error(f"ScheduledTaskListener: Task {task_id} not found")
                return

            start_time = datetime.now(UTC)

            # Import event bus for handler to use
            from marvin.services.event_bus_service.event_bus_service import EventBusService

            event_bus = EventBusService(bg_tasks=None)

            try:
                # Emit started event
                event_bus.dispatch(
                    integration_id="scheduled_tasks",
                    group_id=task.group_id,
                    event_type=EventTypes.scheduled_task_started,
                    document_data=event.document_data,  # Reuse same task data
                    message=f"Scheduled task '{task.name}' execution started",
                )

                # Get and execute handler
                handler = TaskHandlerRegistry.get_handler(task.task_type)
                self.logger.info(f"Executing scheduled task: {task.name} (type: {task.task_type})")
                output = handler.execute(task, event_bus)

                # Calculate duration
                end_time = datetime.now(UTC)
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # Log successful execution
                repos.scheduled_task_executions.log_execution(
                    task_id=task.id,
                    group_id=task.group_id,
                    status="success",
                    executed_at=start_time,
                    duration_ms=duration_ms,
                    output=output,
                )

                # Update task state
                repos.scheduled_tasks.update_execution_state(
                    task_id=task.id,
                    last_run_at=start_time,
                    last_status="success",
                    last_duration_ms=duration_ms,
                    failure_count=0,  # Reset on success
                )

                # Recalculate next_run_at for recurring tasks
                next_run = repos.scheduled_tasks._compute_next_run(task.schedule_type, task.schedule_config)
                if next_run:
                    repos.scheduled_tasks.update_next_run(task.id, next_run)
                elif task.schedule_type == "once":
                    # One-time task — clear next_run_at so scheduler won't re-fire it
                    repos.scheduled_tasks.update_next_run(task.id, None)

                # Emit completed event
                event_bus.dispatch(
                    integration_id="scheduled_tasks",
                    group_id=task.group_id,
                    event_type=EventTypes.scheduled_task_completed,
                    document_data=event.document_data,
                    message=f"Scheduled task '{task.name}' completed successfully in {duration_ms}ms",
                )

                self.logger.info(f"Scheduled task '{task.name}' completed successfully in {duration_ms}ms")

            except ValueError as e:
                # Handler not found
                self.logger.error(f"Scheduled task handler error: {e}")
                self._handle_task_failure(repos, task, start_time, str(e), None, event_bus, event)

            except Exception as e:
                # Handler execution failed
                error_msg = str(e)
                error_trace = traceback.format_exc()
                self.logger.error(f"Scheduled task '{task.name}' failed: {error_msg}\n{error_trace}")
                self._handle_task_failure(repos, task, start_time, error_msg, error_trace, event_bus, event)

    def _handle_task_failure(
        self,
        repos,
        task,
        start_time,
        error_message: str,
        error_traceback: str | None,
        event_bus,
        event: Event,
    ) -> None:
        """Helper to handle task execution failures."""
        end_time = datetime.now(UTC)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Log failed execution
        repos.scheduled_task_executions.log_execution(
            task_id=task.id,
            group_id=task.group_id,
            status="failed",
            executed_at=start_time,
            duration_ms=duration_ms,
            error_message=error_message,
            error_traceback=error_traceback,
        )

        # Update task state with incremented failure count
        repos.scheduled_tasks.update_execution_state(
            task_id=task.id,
            last_run_at=start_time,
            last_status="failed",
            last_duration_ms=duration_ms,
            failure_count=task.failure_count + 1,
        )

        # Still recalculate next_run_at so the task keeps retrying on schedule
        next_run = repos.scheduled_tasks._compute_next_run(task.schedule_type, task.schedule_config)
        if next_run:
            repos.scheduled_tasks.update_next_run(task.id, next_run)

        # Emit failed event
        event_bus.dispatch(
            integration_id="scheduled_tasks",
            group_id=task.group_id,
            event_type=EventTypes.scheduled_task_failed,
            document_data=event.document_data,
            message=f"Scheduled task '{task.name}' failed: {error_message}",
        )


class ConsoleEventListener(EventListenerBase):
    """
    Event listener that logs all events to the console for debugging.

    This listener is useful during development to see events in real-time
    without needing to configure external webhooks or notification services.
    """

    def __init__(self, group_id: UUID4) -> None:
        """
        Initializes the ConsoleEventListener for a specific group.

        Args:
            group_id (UUID4): The ID of the group this listener is associated with.
        """
        from .publisher import ConsolePublisher

        super().__init__(group_id, ConsolePublisher())

    def get_subscribers(self, event: Event) -> list[str]:
        """
        Returns a list of subscribers for console logging.

        For ConsoleEventListener, we always return ["console"] to indicate
        that all events should be logged to the console.

        Args:
            event (Event): The event to log.

        Returns:
            list[str]: Always returns ["console"] to log all events.
        """
        # Always log all events to console
        return ["console"]

    def publish_to_subscribers(self, event: Event, subscribers: list[str]) -> None:
        """
        Publishes the event to the console logger.

        Args:
            event (Event): The event to log.
            subscribers (list[str]): List of subscribers (ignored, always logs to console).
        """
        # Use the ConsolePublisher to log the event
        self.publisher.publish(event, subscribers)


class EmailEventListener(EventListenerBase):
    """
    Event listener that fires email templates when a matching event occurs.

    Reads EmailEventSubscription rows for the group, resolves recipients,
    and sends email via EmailService._send_db_template.
    """

    def __init__(self, group_id) -> None:
        from .publisher import ConsolePublisher

        super().__init__(group_id, ConsolePublisher())

    def get_subscribers(self, event: Event) -> list[Any]:
        if event.event_type == EventTypes.webhook_task:
            return []
        with self.ensure_repos(self.group_id) as repos:
            return repos.email_event_subscriptions.multi_query(
                {"event_type": event.event_type.name, "enabled": True}
            )

    def publish_to_subscribers(self, event: Event, subscribers: list[Any]) -> None:
        from marvin.db.models.groups.email_templates import EmailTemplateModel
        from marvin.db.models.users.workspace_members import WorkspaceMembers
        from marvin.db.models.users.roles import WorkspaceRole
        from marvin.db.models.users import Users
        from marvin.services.email.email_service import EmailService
        from marvin.services.events.event_variables import build_event_variables

        variables = build_event_variables(event)
        email_service = EmailService(group_id=str(self.group_id))

        with self.ensure_session() as session:
            for sub in subscribers:
                template = session.get(EmailTemplateModel, sub.template_id)
                if template is None or not template.enabled:
                    self.logger.warning(f"EmailEventListener: template {sub.template_id} not found or disabled")
                    continue

                recipients = self._resolve_recipients(sub, variables, session)
                if not recipients:
                    self.logger.info(
                        f"EmailEventListener: no recipients for subscription {sub.id} "
                        f"(event={event.event_type.name})"
                    )
                    continue

                for addr in recipients:
                    try:
                        self.logger.info(
                            f"EmailEventListener: sending template '{template.name}' "
                            f"to {addr} for event {event.event_type.name}"
                        )
                        email_service._send_db_template(addr, template, variables)
                    except Exception as exc:
                        self.logger.error(
                            f"EmailEventListener: failed sending to {addr} "
                            f"(template={template.name}, event={event.event_type.name}): {exc}"
                        )

    def _resolve_recipients(self, sub: Any, variables: dict, session) -> list[str]:
        from marvin.db.models.users.workspace_members import WorkspaceMembers
        from marvin.db.models.users.roles import WorkspaceRole
        from marvin.db.models.users import Users
        from sqlalchemy.orm import Session

        match sub.recipient_type:
            case "event_field":
                field = sub.recipient_field
                if field and field in variables:
                    addr = variables[field]
                    if isinstance(addr, str) and addr and "@" in addr:
                        return [addr]
                    self.logger.warning(
                        f"EmailEventListener: event_field '{field}' resolved to non-email value "
                        f"'{addr}' for subscription {sub.id} — possible misconfiguration, skipping"
                    )
                    return []
                return []
            case "specific":
                if not sub.recipient_email:
                    return []
                return [a.strip() for a in sub.recipient_email.split(",") if a.strip()]
            case "admins":
                stmt = (
                    select(Users.email)
                    .join(WorkspaceMembers, WorkspaceMembers.user_id == Users.id)
                    .where(
                        WorkspaceMembers.group_id == self.group_id,
                        WorkspaceMembers.workspace_role.in_(
                            [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]
                        ),
                    )
                )
                rows = session.execute(stmt).scalars().all()
                return [r for r in rows if r]
            case _:
                return []


class AuditLogListener(EventListenerBase):
    """
    Event listener that persists all events to the database for audit trail.

    This listener creates an immutable record of every event that occurs in Marvin,
    enabling event history queries, entity timelines, and user activity tracking.
    It should be registered first in the listener chain to ensure events are
    persisted even if subsequent listeners fail.
    """

    def __init__(self, group_id: UUID4) -> None:
        """
        Initializes the AuditLogListener for a specific group.

        Args:
            group_id (UUID4): The ID of the group this listener is associated with.
        """
        from .publisher import AuditLogPublisher

        super().__init__(group_id, AuditLogPublisher())

    def get_subscribers(self, event: Event) -> list[str]:
        """
        Returns a list of subscribers for audit logging.

        For AuditLogListener, we always return ["database"] to indicate
        that all events should be persisted to the event_log table.

        Args:
            event (Event): The event to persist.

        Returns:
            list[str]: Always returns ["database"] to persist all events.
        """
        # Always persist all events to database
        return ["database"]

    def publish_to_subscribers(self, event: Event, subscribers: list[str]) -> None:
        """
        Publishes the event to the audit log database.

        Args:
            event (Event): The event to persist.
            subscribers (list[str]): List of subscribers (ignored, always persists to database).
        """
        # Use the AuditLogPublisher to persist the event
        self.publisher.publish(event, subscribers)
