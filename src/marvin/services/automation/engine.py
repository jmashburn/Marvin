"""Run a workspace's Flavor B automations for one event.

The listener normalizes an :class:`Event` into a small ``event_ctx`` dict and calls
:func:`run_automations_for_event`. The engine loads the group's enabled automations, builds the
match context (event + the referenced entry), evaluates trigger + conditions, and runs each matching
automation's action pipeline in order — threading ``$previous`` between steps.

Actions dispatch through the action-executor registry (`actions.run_action`) — one executor per
`kind` (operation/emit_event/handler/webhook). The dispatcher is injected (default = the registry) so
the engine is unit-testable without real executors.
"""

from typing import Callable

from .actions import AutomationActionError, run_action as _registry_run_action
from .matcher import matches

MAX_ACTIONS = 10          # per-automation guardrail against a runaway pipeline
MAX_REACTION_DEPTH = 3    # how many automation/emit_event hops a single chain may span before we stop


def _entry_context(session, group_id, entry_id) -> dict | None:
    """Load the minimal entry facts conditions reference (type slug, status, title)."""
    from marvin.db.models.platform.entries import Entries

    entry = session.get(Entries, entry_id)
    if not entry or entry.group_id != group_id:
        return None
    etype = entry.entry_type.slug if entry.entry_type else None
    return {"id": str(entry.id), "entry_type": etype, "status": entry.status,
            "title": entry.title, "slug": entry.slug}


def run_automations_for_event(
    session,
    group_id,
    event_ctx: dict,
    *,
    logger=None,
    run_action: Callable = _registry_run_action,
) -> int:
    """Run every enabled automation matching this event. Returns how many ran (best-effort).

    ``event_ctx`` = ``{"event_type", "entry_id"?, "user_id"?, "reaction_depth"?}``. A single automation
    failing (bad action, provider error) is logged and skipped — never raised, so it can't break
    event dispatch. ``reaction_depth`` is threaded into the context so re-emitting executors bound the
    chain (the listener already refuses past MAX_REACTION_DEPTH).
    """
    from marvin.db.models.groups.automations import WorkspaceAutomationModel

    automations = (
        session.query(WorkspaceAutomationModel)
        .filter_by(group_id=group_id, enabled=True)
        .all()
    )
    if not automations:
        return 0

    depth = int(event_ctx.get("reaction_depth", 0))
    context: dict = {"event": event_ctx, "previous": {}, "depth": depth}
    if event_ctx.get("entry_id"):
        entry_ctx = _entry_context(session, group_id, event_ctx["entry_id"])
        if entry_ctx:
            context["entry"] = entry_ctx

    user_id = event_ctx.get("user_id")
    ran = 0
    for automation in automations:
        defn = automation.definition or {}
        trig = defn.get("trigger") or {}
        if not _trigger_matches(trig, event_ctx):
            continue
        ran_this, ok = _run_targets(
            session, group_id, automation, context,
            user_id=user_id, logger=logger, run_action=run_action, gate_conditions=True,
        )
        if ran_this:
            _announce(session, group_id, automation, ok, depth, user_id, context)
            ran += 1

    return ran


def _target_context(base_context: dict, entity_ref: dict) -> dict:
    """A per-target match context: bind the resolved entity as `entry` and as `$event.entry_id`
    (so entry-defaulting actions target it) while carrying the rest of the base context."""
    base_event = base_context.get("event", {})
    return {**base_context, "event": {**base_event, "entry_id": entity_ref["id"]}, "entry": entity_ref}


def _run_targets(session, group_id, automation, base_context: dict, *, user_id, logger, run_action,
                 gate_conditions: bool) -> tuple[int, bool]:
    """Run the automation's pipeline over its target set (the `target` selector) — or, with no
    target, over the single trigger context.

    Returns ``(ran_count, all_ok)``. With a `target`, conditions are always applied as the WHERE
    over the resolved set. With no target, `gate_conditions` decides (events gate; a manual Run does
    not). Capped by the selector — a matched set larger than the cap is truncated and logged.
    """
    defn = automation.definition or {}
    conditions = defn.get("conditions")
    target = defn.get("target")

    if target:
        from .selector import entity_ref, resolve_target_entities
        try:
            entities, total = resolve_target_entities(session, group_id, target, base_context)
        except Exception as e:
            if logger:
                logger.warning("automation '%s' target query failed: %s", automation.slug, e)
            return 0, True
        if logger and total > len(entities):
            logger.warning(
                "automation '%s' target matched %d entities; acting on the first %d (cap)",
                automation.slug, total, len(entities),
            )
        contexts = [_target_context(base_context, entity_ref(ent)) for ent in entities]
        gate = True  # a target's conditions are its WHERE clause — always applied
    else:
        contexts = [base_context]
        gate = gate_conditions

    ran, ok_all = 0, True
    for ctx in contexts:
        if gate and not matches(conditions, ctx):
            continue
        ok = _run_pipeline(session, group_id, automation, ctx, user_id=user_id, logger=logger, run_action=run_action)
        ok_all = ok_all and ok
        ran += 1
    return ran, ok_all


def _trigger_matches(trig: dict, event_ctx: dict) -> bool:
    """Does this event fire this trigger? Event triggers match by event name; chained/on-error
    triggers match the automation lifecycle events (optionally targeting a specific automation)."""
    ttype = trig.get("type", "event")
    etype = event_ctx.get("event_type")
    if ttype == "event":
        return trig.get("event") == etype
    if ttype == "incoming_webhook":
        # Fire on an incoming_webhook event; an empty/"any" target matches any webhook, else the slug.
        if etype != "incoming_webhook":
            return False
        target = trig.get("webhook")
        return not target or target == "any" or target == event_ctx.get("webhook_slug")
    if ttype == "chained":
        return etype == "automation_ran" and _target_ok(trig, event_ctx)
    if ttype == "on_error":
        return etype == "automation_failed" and _target_ok(trig, event_ctx)
    return False  # manual / schedule — not event-driven


def _target_ok(trig: dict, event_ctx: dict) -> bool:
    """chained/on-error may target a specific source automation (by slug or id); empty/"any" = all."""
    target = trig.get("automation")
    if not target or target == "any":
        return True
    return target in (event_ctx.get("automation_slug"), event_ctx.get("automation_id"))


def _announce(session, group_id, automation, ok: bool, depth: int, user_id, context: dict) -> None:
    """Emit automation_ran / automation_failed so chained + on-error triggers can react.

    Dispatched at reaction_depth+1 so chains stay bounded (the listener refuses past MAX_REACTION_DEPTH).
    Best-effort — never breaks the run.
    """
    from marvin.services.event_bus_service.event_bus_service import EventBusService
    from marvin.services.event_bus_service.event_types import EventAutomationData, EventTypes

    event_type = EventTypes.automation_ran if ok else EventTypes.automation_failed
    try:
        EventBusService(bg_tasks=None).dispatch(
            integration_id="automation",
            group_id=group_id,
            event_type=event_type,
            document_data=EventAutomationData(
                automation_id=automation.id,
                automation_slug=automation.slug,
                ok=ok,
                error=None if ok else context.get("_error"),
                workspace_id=group_id,
            ),
            message=f"Automation '{automation.slug}' {'ran' if ok else 'failed'}",
            user_id=user_id,
            reaction_depth=depth + 1,
        )
    except Exception:
        pass


def _run_pipeline(session, group_id, automation, context: dict, *, user_id, logger, run_action) -> bool:
    """Run one automation's action pipeline in order. Returns True if all steps completed.

    A fresh `previous` is set so pipelines don't leak into each other; a failing step stops the rest
    (later steps usually depend on it).
    """
    actions = (automation.definition or {}).get("actions") or []
    context["previous"] = {}
    context.pop("_error", None)
    for action in actions[:MAX_ACTIONS]:
        try:
            out = run_action(session, group_id, action, context, user_id=user_id)
            context["previous"] = out if isinstance(out, dict) else {}
        except AutomationActionError as e:
            context["_error"] = str(e)
            if logger:
                logger.warning(
                    "automation '%s' action kind=%s failed: %s",
                    automation.slug, action.get("kind"), e,
                )
            return False
    return True


def run_automation_now(session, group_id, automation, *, user_id=None, logger=None, run_action: Callable = _registry_run_action) -> dict:
    """Run one automation on demand (the Manual trigger / Run button) — skips the trigger + condition
    gates (the human explicitly asked for it). No event, so `$event.*` resolves to None; best for
    automations whose steps don't need a specific entry (webhook, handler, reindex, …).
    """
    context: dict = {
        "event": {"event_type": "manual", "user_id": str(user_id) if user_id else None},
        "previous": {},
        "depth": 0,
    }
    # Manual run skips conditions when acting on the single (implicit) context — the human asked for
    # it. But when a `target` selects a set, its conditions are the WHERE over that set and DO apply.
    ran, ok = _run_targets(
        session, group_id, automation, context,
        user_id=user_id, logger=logger, run_action=run_action, gate_conditions=False,
    )
    _announce(session, group_id, automation, ok, 0, user_id, context)
    return {"ok": ok, "ran": ran, "result": context.get("previous", {})}
