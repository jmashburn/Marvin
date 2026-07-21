"""Derive new assets from an existing image — e.g. a cropped thumbnail from a full hero.

One upload can then satisfy a recipe that asks for more than one image: the hero stays the full
image, and a `thumbnail` derivative is a center-cropped square cut from it. Derivatives are ordinary
assets carrying ``metadata_json.derived_from`` (the source id) + ``metadata_json.variant`` (the kind),
so they're traceable back to their source and never re-derived twice.

Kinds are intentionally small for v1: `thumbnail` (a square center-crop). More (palette, enhance) can
register alongside `_TRANSFORMS` without touching callers.
"""

from __future__ import annotations

import io
import uuid
from types import SimpleNamespace

from marvin.core.root_logger import get_logger

_THUMBNAIL_SIZE = 512  # px — the square edge of a thumbnail derivative

# Accepted spellings for each derivation kind → canonical variant name.
_KIND_ALIASES = {
    "thumbnail": "thumbnail", "thumb": "thumbnail", "cropped": "thumbnail", "crop": "thumbnail",
}


class AssetDerivationService:
    """Produce derivative image assets from a source asset. Construct with repos + storage provider."""

    def __init__(self, repos, storage, logger=None):
        self.repos = repos
        self.storage = storage
        self.logger = logger or get_logger(__name__)

    @staticmethod
    def normalize_kind(kind: str) -> str | None:
        """Canonical variant name for a requested derive kind, or None if unsupported."""
        return _KIND_ALIASES.get(str(kind or "").strip().lower())

    def derive(self, source, kind: str, group_id, user_id):
        """Create one derivative asset of `kind` from `source` (an Assets row). Returns the new
        AssetRead. Raises ValueError for a non-image source or an unknown kind."""
        variant = self.normalize_kind(kind)
        if variant is None:
            raise ValueError(f"unknown derivation kind '{kind}'")
        if (getattr(source, "asset_type", None) or "") != "image":
            raise ValueError("can only derive from an image asset")

        raw = self.storage.get(source.storage_key).read()
        out_bytes, ext, mime = self._render(variant, raw)

        from slugify import slugify

        from marvin.schemas.platform.assets import AssetUploadRequest
        from marvin.services.assets.asset_storage_service import AssetStorageService

        base = getattr(source, "filename", None) or "asset"
        name = f"{source.name} ({variant})"
        slug = f"{slugify(name) or 'asset'}-{uuid.uuid4().hex[:6]}"
        upload_file = SimpleNamespace(filename=f"{base}-{variant}.{ext}", file=io.BytesIO(out_bytes))
        request = AssetUploadRequest(
            slug=slug, name=name, alt_text=getattr(source, "alt_text", None),
            metadata_json={"derived_from": str(source.id), "variant": variant},
        )
        return AssetStorageService(self.repos, self.storage).upload_asset(
            upload_file=upload_file, upload_request=request, group_id=group_id, user_id=user_id,
        )

    def fulfill_for_entry(self, entry, group_id, user_id, *, event_bus=None) -> dict:
        """Execute the entry type recipe's per-role ``derive`` steps for the images attached to
        ``entry`` — producing + attaching each derivative (e.g. a thumbnail cut from the hero) so a
        single upload can satisfy a recipe asking for more. Idempotent (skips a variant already
        derived from the same source). Returns ``{"derived": [...], "unmet": [...]}`` — unmet lists
        what could NOT be auto-fulfilled (an unsupported kind, or a required/min slot with no image
        to derive from, e.g. a required gallery photo, which the caller should surface for a human).
        """
        from marvin.db.models.platform import Assets, EntryAssets, EntryTypes
        from marvin.schemas.platform.entry_type_recipe import EntryTypeRecipe
        from marvin.services.entries import EntryService

        session = self.repos.assets.session
        et = session.get(EntryTypes, entry.entry_type_id)
        recipe = EntryTypeRecipe.model_validate((et.recipe_json if et else {}) or {})
        roles = {r.role: r for r in (recipe.assets.roles or [])} if recipe.assets else {}
        if not roles:
            return {"derived": [], "unmet": []}

        rows = session.query(EntryAssets).filter(EntryAssets.entry_id == entry.id).order_by(EntryAssets.position).all()
        # (source_id, variant) pairs already attached — stay idempotent across repeat uploads.
        present: set = set()
        for r in rows:
            a = session.get(Assets, r.asset_id)
            meta = (getattr(a, "metadata_json", None) or {}) if a else {}
            if meta.get("derived_from") and meta.get("variant"):
                present.add((str(meta["derived_from"]), meta["variant"]))

        svc = EntryService(session, group_id, event_bus=event_bus, actor_id=user_id)
        derived: list = []
        unmet: list = []
        for r in list(rows):  # snapshot — we attach more rows as we go
            spec = roles.get(r.role)
            if not spec or not spec.derive:
                continue
            source = session.get(Assets, r.asset_id)
            if not source or (source.asset_type or "") != "image":
                continue
            for kind in spec.derive:
                variant = self.normalize_kind(kind)
                if variant is None:
                    unmet.append({"role": r.role, "kind": kind, "reason": "unsupported derivation"})
                    continue
                if (str(source.id), variant) in present:
                    continue
                try:
                    new_asset = self.derive(source, variant, group_id, user_id)
                    svc.attach_asset(entry.id, new_asset.id, role=variant)
                    present.add((str(source.id), variant))
                    derived.append({"role": variant, "slug": new_asset.slug, "from": source.slug})
                except Exception as e:  # one bad derive shouldn't sink the rest
                    self.logger.warning(f"derive {variant} from {source.slug} failed: {e}")
                    unmet.append({"role": r.role, "kind": kind, "reason": str(e)})

        # Report required / min shortfalls we could NOT derive our way out of (can't invent a photo).
        final = session.query(EntryAssets).filter(EntryAssets.entry_id == entry.id).all()
        by_role: dict = {}
        for r in final:
            by_role[r.role] = by_role.get(r.role, 0) + 1
        if recipe.assets.min and len(final) < recipe.assets.min:
            unmet.append({"reason": f"recipe expects at least {recipe.assets.min} image(s); has {len(final)}"})
        for role_name, spec in roles.items():
            need = spec.min or (1 if spec.required else 0)
            have = by_role.get(role_name, 0)
            if have < need:
                unmet.append({"role": role_name, "reason": f"required — has {have}, needs {need} (no source to derive)"})
        return {"derived": derived, "unmet": unmet}

    def _render(self, variant: str, raw: bytes) -> tuple[bytes, str, str]:
        """Apply the transform for `variant` to the source bytes → (bytes, extension, mime)."""
        from PIL import Image, ImageOps

        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))  # honor camera rotation
        if variant == "thumbnail":
            # ImageOps.fit center-crops to the target aspect (square) then resizes — "the cropped one".
            square = ImageOps.fit(img.convert("RGB"), (_THUMBNAIL_SIZE, _THUMBNAIL_SIZE), Image.LANCZOS)
            buf = io.BytesIO()
            square.save(buf, "JPEG", quality=85)
            return buf.getvalue(), "jpg", "image/jpeg"
        raise ValueError(f"no renderer for variant '{variant}'")  # pragma: no cover
