from typing import Protocol

import apprise
import requests
from fastapi.encoders import jsonable_encoder

from marvin.services.event_bus_service.event_types import Event
from marvin.db.models.groups import Method


class PublisherLike(Protocol):
    def publish(self, event: Event, notification_urls: list[str]): ...


class ApprisePublisher:
    def __init__(self, hard_fail=False) -> None:
        asset = apprise.AppriseAsset(
            async_mode=True,
            image_url_mask="",
        )
        self.apprise = apprise.Apprise(asset=asset)
        self.hard_fail = hard_fail

    def publish(self, event: Event, notification_urls: list[str]):
        """Publishses a list of notification URLs"""

        tags = []
        for dest in notification_urls:
            # we tag the url so it only sends each notification once
            tag = str(event.event_id)
            tags.append(tag)

            status = self.apprise.add(dest, tag=tag)

            if not status and self.hard_fail:
                raise Exception("Apprise URL Add Failed")

        self.apprise.notify(title=event.message.title, body=event.message.body, tag=tags)


class WebhookPublisher:
    def __init__(self, hard_fail=False) -> None:
        self.hard_fail = hard_fail

    def publish(self, event: Event, notification_urls: list[str], method: str = "POST"):
        """Publish a list of notification URLs using the specified HTTP method."""
        event_payload = jsonable_encoder(event)
        for url in notification_urls:
            if method == "GET":
                r = requests.get(url, timeout=15)
            elif method == "POST":
                r = requests.post(url, json=event_payload, timeout=15)
            elif method == "PUT":
                r = requests.put(url, json=event_payload, timeout=15)
            elif method == "DELETE":
                r = requests.delete(url, timeout=15)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if self.hard_fail:
                r.raise_for_status()
