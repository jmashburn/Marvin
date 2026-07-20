"""`handler` action — run an internal task from the scheduled-task handler registry.

Lets an automation trigger the same internal jobs the scheduler runs (e.g. `request_site_rebuild`,
`ai_reindex_embeddings`, `publish_scheduled_entries`) — no AI required. Handlers only read
`group_id` + `task_config`, so a lightweight duck-typed task carries the config.

SECURITY — allowlist: the task registry also holds destructive/maintenance jobs
(`remove_orphaned_assets`, `prune_event_logs`, `prune_ai_executions`, session/invite pruning) and
`run_automation` itself. A workspace-authored automation must NOT be able to invoke those, so this
action only dispatches the explicit content/publishing/index allowlist below. Anything else is
rejected even though it's a valid registry entry. (New safe handlers must be opted in here.)
"""

from types import SimpleNamespace

from .base import AutomationActionError, register_action

# Handlers a workspace automation may run. Content/publishing/index only — never maintenance,
# pruning, or run_automation (which would let an automation re-run automations directly).
AUTOMATION_ALLOWED_HANDLERS: frozenset[str] = frozenset({
    "request_site_rebuild",
    "publish_scheduled_entries",
    "unpublish_expired_entries",
    "ai_reindex_embeddings",
    "resync_smart_collections",
})


@register_action("handler")
def run_handler(session, group_id, action, context, *, user_id=None, authorizer_role=None, dry_run=False) -> dict:
    from marvin.services.event_bus_service.event_bus_service import EventBusService
    from marvin.services.scheduled_tasks.handlers import TaskHandlerRegistry

    from ..authz import HANDLER_MIN_ROLE, ROLE_OWNER, require_role
    from ..matcher import interpolate

    task_type = action.get("task")
    if not task_type:
        raise AutomationActionError("handler action is missing 'task'")
    require_role(ROLE_OWNER if authorizer_role is None else authorizer_role, HANDLER_MIN_ROLE, f"handler '{task_type}'")
    if task_type not in AUTOMATION_ALLOWED_HANDLERS:
        # Distinguish "not a task at all" from "real task, not automation-safe" for a useful message.
        if TaskHandlerRegistry.is_registered(task_type):
            raise AutomationActionError(
                f"task '{task_type}' can't be run from an automation (not on the allowlist). "
                f"Allowed: {', '.join(sorted(AUTOMATION_ALLOWED_HANDLERS))}."
            )
        raise AutomationActionError(f"unknown task handler '{task_type}'")

    handler = TaskHandlerRegistry.get_handler(task_type)
    config = interpolate(action.get("config") or {}, context)

    if dry_run:
        return {"dry_run": True, "kind": "handler", "task": task_type, "config": config}

    task = SimpleNamespace(group_id=group_id, task_config=config)
    try:
        result = handler.execute(task, EventBusService(bg_tasks=None))
    except Exception as e:
        raise AutomationActionError(f"handler '{task_type}' failed: {e}") from e
    return {"result": result}
