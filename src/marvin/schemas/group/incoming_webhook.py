"""Pydantic schemas for workspace incoming (ingress) webhooks.

An incoming webhook is a tokened endpoint: an external POST to its URL emits an `incoming_webhook`
event onto the bus. These schemas cover admin management (CRUD) and token minting. The secret
`token` is only returned to ADMINs (who manage the webhook) — the receiver itself is public and
authenticates purely by the token value.
"""

from datetime import datetime

from pydantic import UUID4, ConfigDict

from marvin.schemas._marvin import _MarvinModel


class IncomingWebhookCreate(_MarvinModel):
    name: str
    slug: str | None = None  # generated from name when omitted
    description: str | None = None
    enabled: bool = False

    model_config = ConfigDict(from_attributes=True)


class IncomingWebhookUpdate(_MarvinModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class IncomingWebhookRead(_MarvinModel):
    id: UUID4
    group_id: UUID4
    name: str
    slug: str
    description: str | None = None
    enabled: bool
    token: str | None = None  # the secret; ADMIN-only surface. Null = no token minted yet.
    received_count: int = 0
    last_received_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
