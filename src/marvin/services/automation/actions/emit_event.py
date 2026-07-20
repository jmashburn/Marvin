"""`emit_event` action — dispatch an internal event to CHAIN other reactions/automations. No AI.

This is what makes Flavor B an orchestrator rather than a one-shot: an automation can re-emit an
internal event (e.g. `entry_published`) that other automations/reactions then handle. To keep chains
finite, the emitted event carries `reaction_depth = current_depth + 1`; the automation listener
refuses to react past `MAX_REACTION_DEPTH` (see engine).

v1 supports entry-lifecycle events, built from the entry already in the automation's context.
"""

import uuid

from .base import AutomationActionError, register_action


@register_action("emit_event")
def run_emit_event(session, group_id, action, context, *, user_id=None) -> dict:
    from marvin.services.event_bus_service.event_bus_service import EventBusService
    from marvin.services.event_bus_service.event_types import EventEntryData, EventOperation, EventTypes

    from ..matcher import interpolate

    ev_name = action.get("event")
    if not ev_name:
        raise AutomationActionError("emit_event action is missing 'event'")
    try:
        event_type = EventTypes[ev_name]
    except KeyError as e:
        raise AutomationActionError(f"unknown event type '{ev_name}'") from e

    depth = int(context.get("depth", 0)) + 1
    entry_ctx = context.get("entry") or {}
    raw_id = interpolate(action.get("entity_id", "$event.entry_id"), context)
    try:
        entry_id = raw_id if isinstance(raw_id, uuid.UUID) else uuid.UUID(str(raw_id))
    except (ValueError, TypeError) as e:
        raise AutomationActionError("emit_event needs a valid entry id (entity_id)") from e

    doc = EventEntryData(
        operation=EventOperation.update,
        entry_id=entry_id,
        entry_title=entry_ctx.get("title"),
        entry_type=entry_ctx.get("entry_type"),
        workspace_id=group_id,
        workspace_name=None,
        author_id=user_id,
    )
    try:
        EventBusService(bg_tasks=None).dispatch(
            integration_id="automation",
            group_id=group_id,
            event_type=event_type,
            document_data=doc,
            message=f"Automation emitted {ev_name}",
            user_id=user_id,
            entity_id=entry_id,
            entity_type="entry",
            reaction_depth=depth,
        )
    except Exception as e:
        raise AutomationActionError(f"emit_event '{ev_name}' failed: {e}") from e
    return {"emitted": ev_name, "reaction_depth": depth}
