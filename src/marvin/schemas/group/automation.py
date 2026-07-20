"""Pydantic schemas for workspace automations (Flavor B: event → conditions → actions).

The `definition` is intentionally a loose dict at the API boundary — the automation engine
validates/executes it. `AutomationOptions` advertises the builder's vocabulary (trigger events,
condition operators, action kinds) so the UI is backend-driven rather than hardcoding it.
"""

from pydantic import UUID4, ConfigDict

from marvin.schemas._marvin import _MarvinModel


class AutomationCreate(_MarvinModel):
    name: str
    slug: str | None = None          # generated from name when omitted
    enabled: bool = False
    definition: dict = {}            # {trigger, conditions, actions} — validated by the engine

    model_config = ConfigDict(from_attributes=True)


class AutomationUpdate(_MarvinModel):
    name: str | None = None
    enabled: bool | None = None
    definition: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class AutomationRead(_MarvinModel):
    id: UUID4
    group_id: UUID4
    name: str
    slug: str
    enabled: bool
    definition: dict = {}
    created_by: UUID4 | None = None

    model_config = ConfigDict(from_attributes=True)


class AutomationActionOption(_MarvinModel):
    """One operation the builder can offer as an `operation` action."""
    op: str
    name: str
    description: str
    entity_types: list[str] = []
    writes_back: bool = False        # whether this op has a write-back map (offer the toggle)

    model_config = ConfigDict(from_attributes=True)


class AutomationWebhookOption(_MarvinModel):
    """One of the workspace's configured webhooks, offered to the `webhook` action."""
    id: UUID4
    name: str
    url: str
    method: str = "POST"

    model_config = ConfigDict(from_attributes=True)


class AutomationTargetOption(_MarvinModel):
    """Another automation in the workspace — a chained/on-error trigger may target it."""
    id: UUID4
    slug: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class AutomationOptions(_MarvinModel):
    """The builder's vocabulary — so the UI doesn't hardcode triggers/ops/operators."""
    trigger_types: list[str] = []        # event | manual (schedule/webhook/chat/mcp/… as they land)
    triggers: list[str] = []             # event names, for trigger_type="event"
    condition_ops: list[str] = []        # eq | neq | contains | exists
    action_kinds: list[str] = []         # operation / emit_event / handler / webhook
    operations: list[AutomationActionOption] = []
    webhooks: list[AutomationWebhookOption] = []   # the workspace's configured webhooks
    automations: list[AutomationTargetOption] = []  # other automations (chained/on-error targets)

    model_config = ConfigDict(from_attributes=True)
