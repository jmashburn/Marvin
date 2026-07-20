"""Built-in ACTION tools — the registry's write capabilities (deterministic entry-linking).

Everything else in the registry is read-only; these mutate. They go through EntryService so each
mutation and its event fires correctly (entry_resource_attached / entry_tag_attached /
asset_attached_to_entry / entry_added_to_collection …) and automations can react. Gated at AUTHOR,
read_only=False. Because they're registry tools they project to MarvinMCP automatically
(marvin_attach_resource, marvin_attach_tag, …) and bind in-process to the agent — one definition,
both surfaces.

This is the "deterministic manipulation" surface: attach/detach a *specific* existing (or
find-or-created) tag / resource / asset / collection to an entry, complementing the AI-authoring
path (compose_entry / generate-tags) which decides links for you.
"""

import json

from ..entity_resolve import resolve_entity_id
from ..operations.base import ROLE_AUTHOR
from .base import ToolContext, register_tool

_ENTRY_ARG = {"type": "string", "description": "the entry by slug or id"}


def _service(ctx: ToolContext):
    from marvin.services.entries import EntryService

    return EntryService(ctx.session, ctx.group_id, actor_id=getattr(ctx.user, "id", None))


def _entry_link(ctx: ToolContext, args: dict, *, method: str, ref_key: str, role: bool = False) -> str:
    """Shared body for the entry-link tools: resolve the entry, call the EntryService method with the
    ref (+ optional role), map the idempotent result to JSON."""
    entry_id = resolve_entity_id(ctx.session, ctx.group_id, "entry", args.get("entry"))
    ref = str(args.get(ref_key) or "")
    kwargs = {"role": args["role"]} if role and args.get("role") else {}
    result = getattr(_service(ctx), method)(entry_id, ref, **kwargs)
    if result is None:
        return json.dumps({"error": f"entry or {ref_key} not found in this workspace — check the entry slug/id and the {ref_key}"})
    return json.dumps({"entry": str(args.get("entry")), ref_key: ref, "result": result})


def _link_schema(ref_key: str, ref_desc: str, *, role: bool = False) -> dict:
    props = {"entry": _ENTRY_ARG, ref_key: {"type": "string", "description": ref_desc}}
    if role:
        props["role"] = {"type": "string", "description": "optional role/label for this link (e.g. 'hero', 'primary')"}
    return {"type": "object", "properties": props, "required": ["entry", ref_key]}


# ── Resources ─────────────────────────────────────────────────────────────────
@register_tool(
    name="attach_resource",
    description="Attach a reusable resource (material, technique, supplier, …) to an entry. Idempotent. Identify the entry by slug/id and the resource by slug/name/id.",
    input_schema=_link_schema("resource", "the resource by slug, name, or id", role=True),
    min_role=ROLE_AUTHOR, read_only=False,
)
def attach_resource(ctx: ToolContext, args: dict) -> str:
    return _entry_link(ctx, args, method="attach_resource", ref_key="resource", role=True)


@register_tool(
    name="detach_resource",
    description="Detach a resource from an entry. Idempotent.",
    input_schema=_link_schema("resource", "the resource by slug, name, or id"),
    min_role=ROLE_AUTHOR, read_only=False,
)
def detach_resource(ctx: ToolContext, args: dict) -> str:
    return _entry_link(ctx, args, method="detach_resource", ref_key="resource")


# ── Tags ──────────────────────────────────────────────────────────────────────
@register_tool(
    name="attach_tag",
    description="Attach a tag to an entry. Find-or-creates the tag by name/slug in the workspace vocabulary, then links it. Idempotent.",
    input_schema=_link_schema("tag", "the tag name or slug (created if new)"),
    min_role=ROLE_AUTHOR, read_only=False,
)
def attach_tag(ctx: ToolContext, args: dict) -> str:
    return _entry_link(ctx, args, method="attach_tag", ref_key="tag")


@register_tool(
    name="detach_tag",
    description="Detach a tag from an entry. Idempotent (the tag itself stays in the vocabulary).",
    input_schema=_link_schema("tag", "the tag name or slug"),
    min_role=ROLE_AUTHOR, read_only=False,
)
def detach_tag(ctx: ToolContext, args: dict) -> str:
    return _entry_link(ctx, args, method="detach_tag", ref_key="tag")


# ── Collections ───────────────────────────────────────────────────────────────
@register_tool(
    name="add_to_collection",
    description="Add an entry to a collection. Idempotent. Identify the entry by slug/id and the collection by slug/name/id.",
    input_schema=_link_schema("collection", "the collection by slug, name, or id"),
    min_role=ROLE_AUTHOR, read_only=False,
)
def add_to_collection(ctx: ToolContext, args: dict) -> str:
    return _entry_link(ctx, args, method="add_to_collection", ref_key="collection")


@register_tool(
    name="remove_from_collection",
    description="Remove an entry from a collection. Idempotent.",
    input_schema=_link_schema("collection", "the collection by slug, name, or id"),
    min_role=ROLE_AUTHOR, read_only=False,
)
def remove_from_collection(ctx: ToolContext, args: dict) -> str:
    return _entry_link(ctx, args, method="remove_from_collection", ref_key="collection")


# ── Assets ────────────────────────────────────────────────────────────────────
@register_tool(
    name="attach_asset",
    description="Attach an existing asset (image/file) to an entry, optionally with a role (e.g. 'hero'). Idempotent. To bring in a NEW image from a URL or bytes, use import_asset first.",
    input_schema=_link_schema("asset", "the asset by slug or id", role=True),
    min_role=ROLE_AUTHOR, read_only=False,
)
def attach_asset(ctx: ToolContext, args: dict) -> str:
    return _entry_link(ctx, args, method="attach_asset", ref_key="asset", role=True)


@register_tool(
    name="detach_asset",
    description="Detach an asset from an entry. Idempotent (the asset itself is not deleted).",
    input_schema=_link_schema("asset", "the asset by slug or id"),
    min_role=ROLE_AUTHOR, read_only=False,
)
def detach_asset(ctx: ToolContext, args: dict) -> str:
    return _entry_link(ctx, args, method="detach_asset", ref_key="asset")
