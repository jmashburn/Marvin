"""`entry` action — act on an entry (publish / unpublish / archive / restore). No AI.

Runs through EntryService, so the mutation and its events (entry_published / entry_unpublished /
entry_archived / entry_restored) fire correctly and chains stay reliable. It targets the triggering
entry (`$event.entry_id`) by default, an entry by slug (`entity_slug`), or an explicit id — so it
pairs with the target selector to act on a whole query: "publish all drafts matching X" is a
`target` selecting drafts + this action, since each matched entry is bound to `$event.entry_id` for
its fan-out row.

`entry.delete` is deliberately NOT offered here.
"""

import uuid

from ..matcher import interpolate
from .base import AutomationActionError, register_action

# entry op → the status the transition moves the entry to. The specific event (published/archived/…)
# is derived by EntryService from the entry's prior status, so these stay declarative.
ENTRY_OPS: dict[str, str] = {
    "publish": "published",
    "unpublish": "draft",
    "archive": "archived",
    "restore": "draft",
}


def _resolve_target(session, group_id, action: dict, context: dict):
    """Resolve which entry to act on: by slug, or an id (default: the triggering entry)."""
    from ..runner import _resolve_entry_id_by_slug

    slug = interpolate(action.get("entity_slug"), context) if action.get("entity_slug") else None
    if slug:
        return _resolve_entry_id_by_slug(session, group_id, str(slug))

    raw = interpolate(action.get("entity_id", "$event.entry_id"), context)
    if not raw:
        raise AutomationActionError(
            "entry action has no target entry — set entity_slug (e.g. $event.payload.entry_slug), "
            "add a Run-on target, or trigger on an entry event"
        )
    try:
        return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))
    except (ValueError, TypeError) as e:
        raise AutomationActionError("entry action needs a valid entry id or slug") from e


@register_action("entry")
def run_entry_action(session, group_id, action: dict, context: dict, *, user_id=None, authorizer_role=None) -> dict:
    from marvin.services.entries import EntryService

    from ..authz import ENTRY_ACTION_MIN_ROLE, ROLE_OWNER, require_role

    op = action.get("op")
    if op not in ENTRY_OPS:
        raise AutomationActionError(f"unknown entry action op '{op}' (expected: {', '.join(ENTRY_OPS)})")

    require_role(ROLE_OWNER if authorizer_role is None else authorizer_role, ENTRY_ACTION_MIN_ROLE, f"entry action '{op}'")

    entity_id = _resolve_target(session, group_id, action, context)

    # Emitted events chain at depth+1 so the loop-guard bounds any cascade.
    depth = int(context.get("depth", 0)) + 1
    svc = EntryService(session, group_id, actor_id=user_id, integration_id="automation")
    entry = svc.set_status(entity_id, ENTRY_OPS[op], reaction_depth=depth)
    if entry is None:
        raise AutomationActionError(f"entry {entity_id} not found in this workspace")
    return {"entry_id": str(entity_id), "op": op, "status": ENTRY_OPS[op]}
