"""Built-in ACTION tools — the registry's first write capabilities.

Everything else in the registry is read-only; these mutate. They go through EntryService so the
mutation and its event (entry_resource_attached / entry_resource_detached) fire correctly and
automations can react. Gated at AUTHOR (a content edit), read_only=False. Because they're registry
tools they project to MarvinMCP automatically (marvin_attach_resource / marvin_detach_resource) and
are bound in-process by the agent — one definition, both surfaces.

Closes the gap where resources could only be linked to entries at seed/import time (there was no
runtime attach path, unlike collections and assets).
"""

import json

from ..entity_resolve import resolve_entity_id
from ..operations.base import ROLE_AUTHOR
from .base import ToolContext, register_tool

_ENTRY_ARG = {"type": "string", "description": "the entry by slug or id"}
_RESOURCE_ARG = {"type": "string", "description": "the resource by slug, name, or id"}


def _service(ctx: ToolContext):
    from marvin.services.entries import EntryService

    return EntryService(ctx.session, ctx.group_id, actor_id=getattr(ctx.user, "id", None))


@register_tool(
    name="attach_resource",
    description="Attach a reusable resource (material, technique, supplier, …) to an entry. Idempotent — attaching one that's already linked is a no-op. Identify the entry by slug/id and the resource by slug/name/id.",
    input_schema={"type": "object", "properties": {
        "entry": _ENTRY_ARG,
        "resource": _RESOURCE_ARG,
        "role": {"type": "string", "description": "optional role/label for this link (e.g. 'primary')"},
    }, "required": ["entry", "resource"]},
    min_role=ROLE_AUTHOR,
    read_only=False,
)
def attach_resource(ctx: ToolContext, args: dict) -> str:
    entry_id = resolve_entity_id(ctx.session, ctx.group_id, "entry", args.get("entry"))
    result = _service(ctx).attach_resource(entry_id, str(args.get("resource") or ""), role=args.get("role"))
    if result is None:
        return json.dumps({"error": "entry or resource not found in this workspace — pass the entry by slug/id and the resource by slug/name/id"})
    return json.dumps({"entry": str(args.get("entry")), "resource": str(args.get("resource")), "result": result})


@register_tool(
    name="detach_resource",
    description="Detach a resource from an entry. Idempotent — detaching one that isn't linked is a no-op. Identify the entry by slug/id and the resource by slug/name/id.",
    input_schema={"type": "object", "properties": {
        "entry": _ENTRY_ARG,
        "resource": _RESOURCE_ARG,
    }, "required": ["entry", "resource"]},
    min_role=ROLE_AUTHOR,
    read_only=False,
)
def detach_resource(ctx: ToolContext, args: dict) -> str:
    entry_id = resolve_entity_id(ctx.session, ctx.group_id, "entry", args.get("entry"))
    result = _service(ctx).detach_resource(entry_id, str(args.get("resource") or ""))
    if result is None:
        return json.dumps({"error": "entry or resource not found in this workspace"})
    return json.dumps({"entry": str(args.get("entry")), "resource": str(args.get("resource")), "result": result})
