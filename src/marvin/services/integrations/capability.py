"""Capability routing — discover connected integrations that provide a given capability.

The single entry point ``integrations_providing(kind, group_id)`` is what a capability resolver
(e.g. media enrichment) calls *first*, before falling back to the workspace model or local code.
It returns pre-authorized handlers (secret resolved, context built), highest-priority first, with
uninstalled/disabled integrations filtered out.

Handlers are pure with respect to Marvin: an image goes in as base64 (the resolver resolves an
asset → bytes), and the provider returns base64 bytes or a URL. The resolver owns all asset I/O —
the provider never touches the database.

Canonical input/output dict shapes per capability kind (the resolver builds inputs / reads outputs):

    image.generate  in {prompt, count?, reference_image_b64?}     out {images: [{image_b64|url}]}
    image.edit      in {image_b64, prompt, strength?}             out {image_b64|url}
    image.describe  in {image_b64, prompt?}                       out {text}
    image.search    in {query, limit?}                            out {results: [{url, metadata?}]}
    image.upscale   in {image_b64, factor?}                       out {image_b64|url}
"""

from dataclasses import dataclass, field

from marvin_integration_sdk import IntegrationContext, IntegrationProvider, get_provider
from pydantic import UUID4

from marvin.core.root_logger import get_logger

from .http_client import build_http

logger = get_logger(__name__)


@dataclass
class CapabilityHandler:
    """A uniform, pre-authorized handle to one connected integration's capability action."""

    capability: str
    priority: int
    cost_hint: str | None
    requires_approval: bool
    integration_id: UUID4
    integration_name: str

    _provider: IntegrationProvider = field(repr=False)
    _action_key: str = field(repr=False)
    _ctx: IntegrationContext = field(repr=False)

    def invoke(self, inputs: dict) -> dict:
        """Run the capability with the canonical inputs for its kind; returns the canonical outputs."""
        return self._provider.run_action(self._action_key, inputs, self._ctx)


@dataclass
class _Snapshot:
    provider: IntegrationProvider
    action_key: str
    capability: str
    priority: int
    cost_hint: str | None
    requires_approval: bool
    config: dict
    secret_ref: str | None
    integration_id: UUID4
    integration_name: str


def _read_snapshots(kind: str, group_id: UUID4) -> list[_Snapshot]:
    """Read enabled group integrations whose (installed) provider has an action advertising `kind`."""
    from marvin.db.db_setup import session_context
    from marvin.db.models.groups.integrations import IntegrationModel

    snaps: list[_Snapshot] = []
    with session_context() as session:
        rows = (
            session.query(IntegrationModel)
            .filter(IntegrationModel.group_id == group_id, IntegrationModel.enabled.is_(True))
            .all()
        )
        for row in rows:
            try:
                provider = get_provider(row.provider)  # skip uninstalled providers
            except KeyError:
                continue
            for action in provider.actions:
                if action.capability == kind:
                    snaps.append(
                        _Snapshot(
                            provider=provider,
                            action_key=action.key,
                            capability=action.capability,
                            priority=action.priority,
                            cost_hint=action.cost_hint,
                            requires_approval=action.requires_approval,
                            config=row.config or {},
                            secret_ref=row.secret_ref,
                            integration_id=row.id,
                            integration_name=row.name,
                        )
                    )
    return snaps


def _build_handlers(snaps: list[_Snapshot], group_id: UUID4, resolve_secret_fn) -> list[CapabilityHandler]:
    """Assemble pre-authorized handlers from snapshots, sorted highest-priority-first."""
    handlers: list[CapabilityHandler] = []
    for snap in snaps:
        secret = resolve_secret_fn(snap.secret_ref, group_id) if snap.secret_ref else None
        ctx = IntegrationContext(config=snap.config, secret=secret, logger=logger, http=build_http())
        handlers.append(
            CapabilityHandler(
                capability=snap.capability,
                priority=snap.priority,
                cost_hint=snap.cost_hint,
                requires_approval=snap.requires_approval,
                integration_id=snap.integration_id,
                integration_name=snap.integration_name,
                _provider=snap.provider,
                _action_key=snap.action_key,
                _ctx=ctx,
            )
        )
    handlers.sort(key=lambda h: h.priority, reverse=True)
    return handlers


def integrations_providing(kind: str, group_id: UUID4) -> list[CapabilityHandler]:
    """Connected integrations in this workspace that provide capability ``kind``.

    Highest-priority first; each handler is pre-authorized (secret resolved, context built).
    Uninstalled or disabled integrations are filtered out. Returns [] if none — the caller
    treats that as "no integration for this kind" and falls through to its next backend.
    """
    from marvin.services.secrets.resolver import resolve_secret

    return _build_handlers(_read_snapshots(kind, group_id), group_id, resolve_secret)
