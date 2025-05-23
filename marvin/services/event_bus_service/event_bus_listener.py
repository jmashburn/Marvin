import contextlib
import json
from abc import ABC, abstractmethod
from collections.abc import Generator
from datetime import datetime, timezone
from typing import cast
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from fastapi.encoders import jsonable_encoder
from pydantic import UUID4
from sqlalchemy import select, func
from sqlalchemy.orm.session import Session

import numpy as np

from marvin.db.db_setup import session_context

from marvin.db.models.groups.webhooks import GroupWebhooksModel, Method
from marvin.repos.repository_factory import AllRepositories
from marvin.schemas.group.event import GroupEventNotifierPrivate
from marvin.schemas.group.webhook import WebhookRead
from marvin.services.webhooks.all_webhooks import get_webhooks, AllWebhooks

from .event_types import Event, EventDocumentType, EventTypes, EventWebhookData, EventOperation, EventNameSpace
from .publisher import ApprisePublisher, PublisherLike, WebhookPublisher


class EventListenerBase(ABC):
    _session: Session | None = None
    _repos: AllRepositories | None = None

    def __init__(self, group_id: UUID4, publisher: PublisherLike) -> None:
        self.group_id = group_id
        self.publisher = publisher
        self._session = None
        self._repos = None
        self._webhooks = None

    @abstractmethod
    def get_subscribers(self, event: Event) -> list:
        """Get a list of all subscribers to this event"""
        ...

    @abstractmethod
    def publish_to_subscribers(self, event: Event, subscribers: list) -> None:
        """Publishes the event to all subscribers"""
        ...

    @contextlib.contextmanager
    def ensure_session(self) -> Generator[Session, None, None]:
        """
        ensure_session ensures that a session is available for the caller by checking if a session
        was provided during construction, and if not, creating a new session with the `with_session`
        function and closing it when the context manager exits.

        This is _required_ when working with sessions inside an event bus listener where the listener
        may be constructed during a request where the session is provided by the request, but the when
        run as a scheduled task, the session is not provided and must be created.
        """
        if self._session is None:
            with session_context() as session:
                self._session = session
                yield self._session
        else:
            yield self._session

    @contextlib.contextmanager
    def ensure_repos(self, group_id: UUID4) -> Generator[AllRepositories, None, None]:
        if self._repos is None:
            with self.ensure_session() as session:
                self._repos = AllRepositories(session, group_id=group_id)
                yield self._repos
        else:
            yield self._repos

    @contextlib.contextmanager
    def ensure_webhooks(self, group_id: UUID4) -> Generator[AllWebhooks, None, None]:
        if self._webhooks is None:
            with self.ensure_session() as session:
                self._webhooks = get_webhooks(session, group_id=group_id)
                yield self._webhooks
        else:
            yield self._webhooks


class AppriseEventListener(EventListenerBase):
    _option_value = "option"

    def __init__(self, group_id: UUID4) -> None:
        super().__init__(group_id, ApprisePublisher())

    def get_subscribers(self, event: Event) -> list[str]:
        with self.ensure_repos(self.group_id) as repos:
            notifiers: list[GroupEventNotifierPrivate] = repos.group_event_notifier.multi_query(
                {"enabled": True}, override_schema=GroupEventNotifierPrivate
            )
            urls = [
                notifier.apprise_url
                for notifier in notifiers
                for option in notifier.options
                if getattr(option, self._option_value)
                == EventNameSpace.namespace.value + "." + event.event_type.name.replace("_", "-")
            ]
            urls = AppriseEventListener.update_urls_with_event_data(urls, event)

        return urls

    def publish_to_subscribers(self, event: Event, subscribers: list[str]) -> None:
        self.publisher.publish(event, subscribers)

    @staticmethod
    def update_urls_with_event_data(urls: list[str], event: Event):
        params = {
            "event_type": event.event_type.name,
            "integration_id": event.integration_id,
            "document_data": json.dumps(jsonable_encoder(event.document_data)),
            "event_id": str(event.event_id),
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        }

        return [
            # We use query params to add custom key: value pairs to the Apprise payload by prepending the key with ":".
            (
                AppriseEventListener.merge_query_parameters(url, {f":{k}": v for k, v in params.items()})
                # only certain endpoints support the custom key: value pairs, so we only apply them to those endpoints
                if AppriseEventListener.is_custom_url(url)
                else url
            )
            for url in urls
        ]

    @staticmethod
    def merge_query_parameters(url: str, params: dict):
        scheme, netloc, path, query_string, fragment = urlsplit(url)

        # merge query params
        query_params = parse_qs(query_string)
        query_params.update(params)
        new_query_string = urlencode(query_params, doseq=True)

        return urlunsplit((scheme, netloc, path, new_query_string, fragment))

    @staticmethod
    def is_custom_url(url: str):
        url = str(url)
        return url.split(":", 1)[0].lower() in [
            "form",
            "forms",
            "json",
            "jsons",
            "xml",
            "xmls",
        ]


class WebhookEventListener(EventListenerBase):
    def __init__(
        self,
        group_id: UUID4,
    ) -> None:
        super().__init__(group_id, WebhookPublisher())

    def get_subscribers(self, event: Event) -> list[WebhookRead]:
        if not (event.event_type == EventTypes.webhook_task and isinstance(event.document_data, EventWebhookData)):
            return []

        scheduled_webhooks = self.get_scheduled_webhooks(
            event.document_data.webhook_start_dt, event.document_data.webhook_end_dt
        )
        return scheduled_webhooks

    # def publish_to_subscribers(self, event: Event, subscribers: list[str]) -> None:
    def publish_to_subscribers(self, event: Event, subscribers: list[WebhookRead]) -> None:
        with self.ensure_repos(self.group_id) as repos:
            # We want to check a registry of registered webhooks to see if any of them are
            # are with the name event.document_data.webhook_type.  If a type is registered, we
            # can use that pull the registered funmction and call it with the event data
            # return the result of that function to the webhook url

            data = {}
            webhook_data = cast(EventWebhookData, event.document_data)
            for webhook in subscribers:
                # Here we get webhook_type and choose from reg of webhooks to run command output
                with self.ensure_webhooks(self.group_id) as webhooks:
                    if hasattr(webhooks, webhook.webhook_type.name):
                        webhook_type = getattr(webhooks, webhook.webhook_type.name)
                        if webhook_type:
                            # If the webhook type is registered, we can call it with the event data
                            # and return the result to the webhook url
                            if event.document_data.operation == EventOperation.info:
                                data = webhook_type.info()

                event.document_data.document_type = webhook.webhook_type

                if data:
                    webhook_data.webhook_body = data
                    self.publisher.publish(event, [webhook.url], method=webhook.method.name)

        return True

    def get_scheduled_webhooks(self, start_dt: datetime, end_dt: datetime) -> list[WebhookRead]:
        """Fetches all scheduled webhooks from the database"""

        with self.ensure_session() as session:
            stmt = select(GroupWebhooksModel).where(
                GroupWebhooksModel.enabled == True,  # noqa: E712 - required for SQLAlchemy comparison
                GroupWebhooksModel.scheduled_time > start_dt.astimezone(timezone.utc).time(),
                GroupWebhooksModel.scheduled_time <= end_dt.astimezone(timezone.utc).time(),
                GroupWebhooksModel.group_id == self.group_id,
            )
            return session.execute(stmt).scalars().all()
