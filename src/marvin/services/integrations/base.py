"""
Base class and registry for integration providers.

An integration *instance* (IntegrationModel row) is user data — "my Vercel deploy hook".
An integration *provider* (this registry) is code — what a Vercel integration *is*: the
credentials it needs, the actions it exposes to automations, and the events it emits onto
the bus. Mirrors the OPERATION_REGISTRY / tool-registry pattern: define once, project out.

A provider is a manifest; the existing engines do the work:
  - credentials  -> the secret backend (resolve_secret)
  - actions      -> the automation engine (via an "integration" action kind)
  - emits        -> the event bus (EventBusService.dispatch, integration_id=<slug>)
"""

from abc import ABC
from dataclasses import asdict, dataclass, field
from datetime import datetime
from logging import Logger
from typing import TYPE_CHECKING, Optional

from pydantic import UUID4
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from marvin.services.event_bus_service.event_bus_service import EventBusService

# Provider categories — drive UI grouping and answer "which way does data flow?".
CATEGORY_SOURCE = "source"  # pulls external content in (RSS, cloud storage, git)
CATEGORY_DESTINATION = "destination"  # pushes content out on events (deploy hook, search index)
CATEGORY_CAPABILITY = "capability"  # provides tools/AI capability
CATEGORY_NOTIFY = "notify"  # sends notifications (Slack, Discord)
CATEGORIES = (CATEGORY_SOURCE, CATEGORY_DESTINATION, CATEGORY_CAPABILITY, CATEGORY_NOTIFY)


@dataclass(frozen=True)
class CredentialField:
    """A secret this provider needs. Drives the create form + secret_ref storage."""

    key: str  # "token", "hook_url", "api_key"
    label: str
    help: str = ""
    required: bool = True


@dataclass(frozen=True)
class ProviderEvent:
    """An inbound event this integration can drop on the bus (polled or webhook-pushed)."""

    key: str  # e.g. "rss.item_published"
    label: str
    description: str = ""


@dataclass(frozen=True)
class ProviderAction:
    """An outbound action this integration exposes to automation workflows."""

    key: str  # e.g. "trigger_deploy"
    label: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)  # JSON schema for the action's args


@dataclass
class PolledEvent:
    """An event a source provider produced, ready to dispatch onto the bus."""

    event_key: str  # matches a ProviderEvent.key this provider declared in `emits`
    dedup_key: str  # stable id (feed guid, etc.) so the scheduler can skip duplicates (Phase B)
    message: str = ""
    payload: dict = field(default_factory=dict)


@dataclass
class IntegrationContext:
    """Resolved per-call context handed to provider methods (cf. OperationContext / ToolContext)."""

    integration_id: UUID4
    group_id: UUID4
    slug: str
    config: dict
    secret: str | None  # already resolved via resolve_secret(secret_ref, group_id)
    session: Session
    logger: Logger
    event_bus: Optional["EventBusService"] = None


class IntegrationProvider(ABC):
    """
    A named external-service provider. Subclasses declare capability surfaces and
    implement whichever lifecycle hooks they support.
    """

    slug: str  # registry key, e.g. "vercel_deploy"
    name: str  # "Vercel Deploy Hook"
    description: str = ""
    category: str = CATEGORY_DESTINATION
    config_schema: dict = {}  # JSON schema for `config`, validated on create/update
    credentials: tuple[CredentialField, ...] = ()
    emits: tuple[ProviderEvent, ...] = ()
    actions: tuple[ProviderAction, ...] = ()
    projects_tools: tuple[str, ...] = ()  # tool-registry slugs this integration lights up (optional)

    # --- lifecycle (override what you support) ---

    def check(self, ctx: IntegrationContext) -> tuple[str, str | None]:
        """Health probe → (status, error). Default: ok if a credential is present when required."""
        if self.credentials and any(c.required for c in self.credentials) and not ctx.secret:
            return ("unconfigured", "Missing credential.")
        return ("ok", None)

    def run_action(self, key: str, args: dict, ctx: IntegrationContext) -> dict:
        """Run an action declared in `actions`. Called by the automation engine / test-fire."""
        raise NotImplementedError(f"{self.slug} does not implement actions")

    def poll(self, ctx: IntegrationContext) -> list[PolledEvent]:
        """For polled sources: produce events to dispatch. Called by the scheduler (Phase B)."""
        return []

    def on_webhook(self, payload: dict, ctx: IntegrationContext) -> PolledEvent | None:
        """For webhook-pushed sources: translate a raw payload into a bus event."""
        return None

    # --- action lookup helper ---

    def get_action(self, key: str) -> ProviderAction | None:
        return next((a for a in self.actions if a.key == key), None)

    def info(self) -> dict:
        """Projected to the frontend (and optionally MarvinMCP) as the provider catalog entry."""
        return {
            "slug": self.slug,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "config_schema": self.config_schema,
            "credentials": [asdict(c) for c in self.credentials],
            "emits": [asdict(e) for e in self.emits],
            "actions": [asdict(a) for a in self.actions],
        }


INTEGRATION_REGISTRY: dict[str, IntegrationProvider] = {}


def register_provider(cls):
    """Class decorator that adds the provider to the global registry."""
    INTEGRATION_REGISTRY[cls.slug] = cls()
    return cls


def get_provider(slug: str) -> IntegrationProvider:
    if slug not in INTEGRATION_REGISTRY:
        raise KeyError(f"integration provider '{slug}' not found. Available: {list(INTEGRATION_REGISTRY)}")
    return INTEGRATION_REGISTRY[slug]


def list_providers() -> list[IntegrationProvider]:
    return list(INTEGRATION_REGISTRY.values())


# Re-exported for convenience alongside the datetime type used in schemas.
__all__ = [
    "CredentialField",
    "ProviderEvent",
    "ProviderAction",
    "PolledEvent",
    "IntegrationContext",
    "IntegrationProvider",
    "INTEGRATION_REGISTRY",
    "register_provider",
    "get_provider",
    "list_providers",
    "datetime",
]
