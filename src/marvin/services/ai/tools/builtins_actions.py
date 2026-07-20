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
from types import SimpleNamespace

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


# ── Asset ingestion (bring a new image in) ────────────────────────────────────
_MAX_IMPORT_BYTES = 20 * 1024 * 1024  # 20 MB


@register_tool(
    name="import_asset",
    description=(
        "Bring a NEW image into the workspace as an asset — from a web URL or from base64 bytes "
        "(e.g. a phone capture) — and optionally attach it to an entry in one call. Returns the new "
        "asset id + url. Use attach_asset instead when the asset already exists."
    ),
    input_schema={"type": "object", "properties": {
        "url": {"type": "string", "description": "an http(s) URL of the image to fetch"},
        "data": {"type": "string", "description": "base64-encoded image bytes (alternative to url)"},
        "filename": {"type": "string", "description": "filename for base64 data (e.g. 'photo.jpg')"},
        "name": {"type": "string", "description": "display name (defaults to the filename)"},
        "alt_text": {"type": "string", "description": "accessibility alt text"},
        "attach_to": {"type": "string", "description": "optional entry (slug/id) to attach the new asset to"},
        "role": {"type": "string", "description": "role for the attachment (e.g. 'hero'), if attach_to is set"},
    }},
    min_role=ROLE_AUTHOR, read_only=False,
)
def import_asset(ctx: ToolContext, args: dict) -> str:
    import base64
    import io
    import os
    import uuid as _uuid

    if getattr(ctx.user, "id", None) is None:
        return json.dumps({"error": "import_asset requires an authenticated user"})

    url, data = args.get("url"), args.get("data")
    # 1) Get the bytes + a filename.
    if url:
        if not str(url).lower().startswith(("http://", "https://")):
            return json.dumps({"error": "url must be http(s)"})
        try:
            import httpx

            resp = httpx.get(str(url), timeout=15.0, follow_redirects=True)
            resp.raise_for_status()
            raw = resp.content
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"could not fetch url: {e}"})
        filename = os.path.basename(str(url).split("?")[0]) or "imported"
    elif data:
        try:
            raw = base64.b64decode(str(data), validate=True)
        except Exception as e:  # noqa: BLE001
            return json.dumps({"error": f"invalid base64 data: {e}"})
        filename = args.get("filename") or "imported.png"
    else:
        return json.dumps({"error": "provide either 'url' or 'data' (base64)"})

    if not raw:
        return json.dumps({"error": "no image bytes"})
    if len(raw) > _MAX_IMPORT_BYTES:
        return json.dumps({"error": f"image too large ({len(raw)} bytes; max {_MAX_IMPORT_BYTES})"})

    # 2) Store it as an asset (metadata — mime/type/dimensions — is derived from the bytes).
    from slugify import slugify

    from marvin.repos.all_repositories import get_repositories
    from marvin.schemas.platform.assets import AssetUploadRequest
    from marvin.services.assets.asset_storage_service import AssetStorageService
    from marvin.services.storage.provider_factory import get_storage_provider

    name = (args.get("name") or os.path.splitext(filename)[0] or "imported").strip()
    slug = f"{slugify(name) or 'asset'}-{_uuid.uuid4().hex[:6]}"  # suffix guarantees uniqueness
    upload_file = SimpleNamespace(filename=filename, file=io.BytesIO(raw))
    repos = get_repositories(ctx.session, group_id=ctx.group_id)
    try:
        asset = AssetStorageService(repos, get_storage_provider()).upload_asset(
            upload_file=upload_file,
            upload_request=AssetUploadRequest(slug=slug, name=name, alt_text=args.get("alt_text")),
            group_id=ctx.group_id,
            user_id=ctx.user.id,
        )
    except Exception as e:  # noqa: BLE001
        return json.dumps({"error": f"could not import asset: {e}"})

    out = {"asset_id": str(asset.id), "slug": asset.slug, "name": asset.name,
           "url": getattr(asset, "public_url", None) or getattr(asset, "url", None),
           "assetType": getattr(asset, "asset_type", None)}

    # 3) Optionally attach it to an entry in the same call.
    if args.get("attach_to"):
        entry_id = resolve_entity_id(ctx.session, ctx.group_id, "entry", args["attach_to"])
        out["attach"] = _service(ctx).attach_asset(entry_id, asset.id, role=args.get("role"))
        out["attached_to"] = str(args["attach_to"])
    return json.dumps(out)
