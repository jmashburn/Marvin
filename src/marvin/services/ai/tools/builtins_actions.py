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


# ── Tags (entry / asset / resource — one shared vocabulary) ───────────────────
# Single OR bulk: name one target (`entity`), several (`entities`), or select assets/resources by
# `filter` (type/substring). One or many `tag`/`tags`. Every (target × tag) pair is linked through
# the shared link_tag chokepoint, then asset/resource smart-collection membership is re-materialized
# (entries sync reactively; assets/resources have no reactive listener, so we resync here — the same
# thing the HTTP tags endpoint does — otherwise a freshly-tagged asset never joins its collection).
_BULK_CAP = 1000
_TAG_SCHEMA = {"type": "object", "properties": {
    "entity_type": {"type": "string", "enum": ["entry", "asset", "resource"], "description": "what to tag (default 'entry')"},
    "entity": {"type": "string", "description": "a single entry/asset/resource by slug or id"},
    "entities": {"type": "array", "items": {"type": "string"}, "description": "several targets by slug or id (bulk)"},
    "filter": {"type": "object", "description": "select targets in bulk instead of naming them (dimensions mirror smart-collection rules)", "properties": {
        "entry_types": {"type": "array", "items": {"type": "string"}, "description": "entry type slugs — entries only"},
        "statuses": {"type": "array", "items": {"type": "string"}, "description": "entry statuses (e.g. ['published']) — entries only"},
        "asset_types": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['image','svg'] — assets only"},
        "resource_types": {"type": "array", "items": {"type": "string"}, "description": "resource types — resources only"},
        "tags": {"type": "array", "items": {"type": "string"}, "description": "select targets already carrying ANY of these tags (slug/name) — all types"},
        "query": {"type": "string", "description": "title/name/filename substring (all types)"},
    }},
    "tag": {"type": "string", "description": "a tag name or slug"},
    "tags": {"type": "array", "items": {"type": "string"}, "description": "several tags (each applied to every target)"},
}}


def _narrow_by_tags(session, group_id, q, Model, Junction, fk: str, filt: dict):
    """Narrow `q` to rows carrying ANY of filt['tags'] (by slug or name). Returns (q, ok);
    ok=False means the filter names only tags that don't exist here → no rows can match."""
    refs = [str(t) for t in (filt.get("tags") or []) if str(t).strip()]
    if not refs:
        return q, True
    from marvin.db.models.platform.tags import Tags

    tag_ids = [r[0] for r in session.query(Tags.id).filter(
        Tags.group_id == group_id, Tags.slug.in_(refs) | Tags.name.in_(refs)).all()]
    if not tag_ids:
        return q, False
    sub = session.query(getattr(Junction, fk)).filter(Junction.tag_id.in_(tag_ids))
    return q.filter(Model.id.in_(sub)), True


def _resolve_targets(ctx: ToolContext, entity_type: str, args: dict) -> tuple[list, str | None]:
    """Resolve the target entity ids from `entity` / `entities` / `filter`. Returns (ids, error)."""
    import uuid as _uuid

    refs = ([args["entity"]] if args.get("entity") else []) + list(args.get("entities") or [])
    if refs:
        ids = [resolve_entity_id(ctx.session, ctx.group_id, entity_type, r) for r in refs]
        return [i for i in ids if isinstance(i, _uuid.UUID)], None

    s, gid = ctx.session, ctx.group_id
    filt = args.get("filter") or {}
    if entity_type == "entry":
        from marvin.db.models.platform.entries import Entries
        from marvin.db.models.platform.entry_tags import EntryTags
        from marvin.db.models.platform.entry_types import EntryTypes
        q = s.query(Entries.id).filter(Entries.group_id == gid)
        if filt.get("entry_types"):
            q = q.join(EntryTypes, Entries.entry_type_id == EntryTypes.id).filter(EntryTypes.slug.in_(list(filt["entry_types"])))
        if filt.get("statuses"):
            q = q.filter(Entries.status.in_(list(filt["statuses"])))
        if filt.get("query"):
            t = f"%{filt['query']}%"
            q = q.filter(Entries.title.ilike(t) | Entries.slug.ilike(t))
        q, ok = _narrow_by_tags(s, gid, q, Entries, EntryTags, "entry_id", filt)
        return ([r[0] for r in q.limit(_BULK_CAP).all()] if ok else []), None
    if entity_type == "asset":
        from marvin.db.models.platform.asset_tags import AssetTags
        from marvin.db.models.platform.assets import Assets
        q = s.query(Assets.id).filter(Assets.group_id == gid)
        if filt.get("asset_types"):
            q = q.filter(Assets.asset_type.in_(list(filt["asset_types"])))
        if filt.get("query"):
            t = f"%{filt['query']}%"
            q = q.filter(Assets.original_filename.ilike(t) | Assets.name.ilike(t))
        q, ok = _narrow_by_tags(s, gid, q, Assets, AssetTags, "asset_id", filt)
        return ([r[0] for r in q.limit(_BULK_CAP).all()] if ok else []), None
    if entity_type == "resource":
        from marvin.db.models.platform.resource_tags import ResourceTags
        from marvin.db.models.platform.resources import Resources
        q = s.query(Resources.id).filter(Resources.group_id == gid)
        if filt.get("resource_types"):
            q = q.filter(Resources.resource_type.in_(list(filt["resource_types"])))
        if filt.get("query"):
            t = f"%{filt['query']}%"
            q = q.filter(Resources.name.ilike(t) | Resources.slug.ilike(t))
        q, ok = _narrow_by_tags(s, gid, q, Resources, ResourceTags, "resource_id", filt)
        return ([r[0] for r in q.limit(_BULK_CAP).all()] if ok else []), None
    return [], None  # entity_type is validated upstream; no target given


def _resync_collections(ctx: ToolContext, entity_type: str, ids) -> int:
    """Re-materialize asset/resource smart-collection membership after tag changes. Entries sync via
    SmartCollectionReactionListener; assets/resources have no reactive listener, so we do it here."""
    if entity_type not in ("asset", "resource") or not ids:
        return 0
    from marvin.db.models.platform import Assets, Resources
    from marvin.services.collections.smart_collections import sync_item

    model = {"asset": Assets, "resource": Resources}[entity_type]
    changed = 0
    for eid in ids:
        item = ctx.session.get(model, eid)
        if item:
            changed += sync_item(ctx.session, ctx.group_id, item, entity_type)
    if changed:
        ctx.session.commit()
    return changed


def _tag_link(ctx: ToolContext, args: dict, *, attach: bool) -> str:
    from marvin.services.tagging import TAGGABLE, link_tag

    entity_type = str(args.get("entity_type") or "entry").lower()
    if entity_type not in TAGGABLE:
        return json.dumps({"error": f"entity_type must be one of {list(TAGGABLE)}"})

    tags = [str(t).strip() for t in (([args["tag"]] if args.get("tag") else []) + list(args.get("tags") or [])) if str(t).strip()]
    if not tags:
        return json.dumps({"error": "provide a tag (or tags[]) to apply"})

    ids, err = _resolve_targets(ctx, entity_type, args)
    if err:
        return json.dumps({"error": err})
    if not ids:
        return json.dumps({"error": f"no matching {entity_type}(s) for the given entity/entities/filter"})

    actor_id = getattr(ctx.user, "id", None)
    changed, unchanged, not_found, touched = 0, 0, 0, set()
    for eid in ids:
        for tag in tags:
            res = link_tag(ctx.session, ctx.group_id, entity_type, eid, tag, attach=attach, actor_id=actor_id)
            if res in ("attached", "detached"):
                changed += 1
                touched.add(eid)
            elif res in ("exists", "absent"):
                unchanged += 1
            else:
                not_found += 1

    resynced = _resync_collections(ctx, entity_type, touched)
    verb = "attached" if attach else "detached"
    out = {
        "entity_type": entity_type, "tags": tags,
        "targets": len(ids), verb: changed, "unchanged": unchanged, "not_found": not_found,
        "collections_resynced": resynced,
    }
    # Preserve the simple single-target shape when exactly one entity + one tag was given.
    if args.get("entity") and not args.get("entities") and not args.get("filter") and len(tags) == 1:
        out["entity"] = str(args.get("entity"))
        out["tag"] = tags[0]
        out["result"] = verb if changed else ("exists" if attach else "absent") if unchanged else "not_found"
    return json.dumps(out)


@register_tool(
    name="attach_tag",
    description=(
        "Attach a tag to entries/assets/resources (set entity_type). Find-or-creates the tag in the one "
        "shared workspace vocabulary, links it, and updates smart collections. Idempotent. SINGLE or BULK: "
        "name one target with `entity`, several with `entities`, or select in bulk with `filter` (entries by "
        "entry_types/statuses, assets by asset_types, resources by resource_types, ALL by tags/query — so you "
        "can re-tag everything already carrying a tag); apply one `tag` or many `tags`. One call tags the set."
    ),
    input_schema=_TAG_SCHEMA,
    min_role=ROLE_AUTHOR, read_only=False,
)
def attach_tag(ctx: ToolContext, args: dict) -> str:
    return _tag_link(ctx, args, attach=True)


@register_tool(
    name="detach_tag",
    description=(
        "Detach a tag from entries/assets/resources (set entity_type). Idempotent (the tag stays in the "
        "vocabulary). SINGLE or BULK: `entity`, `entities`, or `filter`; one `tag` or many `tags`."
    ),
    input_schema=_TAG_SCHEMA,
    min_role=ROLE_AUTHOR, read_only=False,
)
def detach_tag(ctx: ToolContext, args: dict) -> str:
    return _tag_link(ctx, args, attach=False)


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


def _public_url_error(url: str) -> str | None:
    """SSRF fence: reject a fetch URL that isn't http(s) or whose host resolves to a non-public
    address (loopback / private / link-local / reserved — e.g. 127.0.0.1, 169.254.169.254, 10.x).
    Returns an error string, or None if the URL is safe to fetch. Callers must also disable redirect
    following so a public host can't 302 into an internal one."""
    import ipaddress
    import socket
    from urllib.parse import urlparse

    parsed = urlparse(str(url))
    if parsed.scheme not in ("http", "https"):
        return "url must be http(s)"
    host = parsed.hostname
    if not host:
        return "url has no host"
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        return f"could not resolve host: {e}"
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return "url resolves to a non-public address — blocked"
    return None


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
        ssrf = _public_url_error(url)
        if ssrf:
            return json.dumps({"error": ssrf})
        try:
            import httpx

            # follow_redirects=False so a public host can't 302 the request into an internal address
            # (the SSRF fence only validated the initial host). A redirect is reported, not chased.
            resp = httpx.get(str(url), timeout=15.0, follow_redirects=False)
            if resp.is_redirect:
                return json.dumps({"error": "url redirects — provide the direct image URL"})
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
