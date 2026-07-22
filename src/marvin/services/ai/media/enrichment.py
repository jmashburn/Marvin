"""Media enrichment — execute a recipe's local ``derive`` media tokens on an entry's images.

Phase 1: deterministic, local Pillow ops (grade/crop) only — no model, no provider, no cost.
For each image linked in a role whose recipe ``derive`` list carries a media token, produce a
transformed derivative asset (with provenance back to the source) and link it to the entry under
a derived role (e.g. ``hero`` → ``hero-grade``). The source asset is never mutated.

Best-effort (a bad image never breaks the caller) and idempotent per (source asset, token): a
derivative that already exists on the entry is skipped, so re-running compose won't double-grade.
"""

from __future__ import annotations

import logging

from marvin.services.ai.media import transforms
from marvin.services.assets.asset_storage_service import AssetStorageService
from marvin.services.storage.provider_factory import get_storage_provider

logger = logging.getLogger(__name__)


class MediaEnrichmentService:
    def __init__(self, session, repos, group_id, user_id=None) -> None:
        self.session = session
        self.repos = repos
        self.group_id = group_id
        self.user_id = user_id

    def run_for_entry(self, entry_id) -> list[str]:
        """Derive media variants for one entry per its type's recipe. Returns human-readable
        summaries of what was produced (empty when the recipe declares no media tokens)."""
        from marvin.db.models.platform.assets import Assets
        from marvin.db.models.platform.entries import Entries
        from marvin.db.models.platform.entry_assets import EntryAssets
        from marvin.db.models.platform.entry_types import EntryTypes
        from marvin.schemas.platform.entry_type_recipe import EntryTypeRecipe

        entry = self.session.get(Entries, entry_id)
        if entry is None or not entry.entry_type_id:
            return []
        entry_type = self.session.get(EntryTypes, entry.entry_type_id)
        if entry_type is None or not entry_type.recipe_json:
            return []

        try:
            recipe = EntryTypeRecipe.model_validate(entry_type.recipe_json or {})
        except Exception as e:  # noqa: BLE001
            logger.debug("media: recipe parse failed for %s: %s", entry_id, e)
            return []
        if not recipe.assets or not recipe.assets.roles:
            return []

        # role -> media tokens declared for it
        role_tokens = {
            r.role: [t for t in (r.derive or []) if transforms.is_media_token(t)]
            for r in recipe.assets.roles
        }
        role_tokens = {role: toks for role, toks in role_tokens.items() if toks}
        if not role_tokens:
            return []

        assets_svc = AssetStorageService(self.repos, get_storage_provider())

        # Derivatives already on this entry — keyed (source_asset_id, token) — for idempotency.
        already: set[tuple[str, str]] = set()
        for a in entry.assets:
            mj = a.metadata_json or {}
            if mj.get("derived_from") and mj.get("derivation"):
                already.add((str(mj["derived_from"]), str(mj["derivation"])))

        summaries: list[str] = []
        for ea in list(entry.entry_assets):
            tokens = role_tokens.get(ea.role)
            if not tokens:
                continue
            src = self.session.get(Assets, ea.asset_id)
            if src is None or not transforms.can_transform(src.mime_type):
                continue
            for token in tokens:
                if (str(src.id), token) in already:
                    continue
                op, _, arg = token.partition(":")
                slug = f"{src.slug}--{op}-{arg}".replace(":", "-").replace("/", "-")[:200]
                try:
                    # Reuse an existing derivative of this (source, token) — the transform is
                    # deterministic, so a hero shared by two entries produces one graded asset
                    # linked to both (reuse-first, like resources).
                    new_asset = self.session.query(Assets).filter(
                        Assets.group_id == self.group_id, Assets.slug == slug,
                    ).first()
                    if new_asset is None:
                        out = transforms.apply_token(token, assets_svc.read_bytes(src.storage_key))
                        if not out:
                            continue
                        name = f"{src.name or src.filename} ({op} {arg})".strip()
                        new_asset = assets_svc.create_derivative(
                            source=src, data=out, group_id=self.group_id,
                            derivation=token, slug=slug, name=name, user_id=self.user_id,
                        )
                    already_linked = self.session.query(EntryAssets).filter(
                        EntryAssets.entry_id == entry.id, EntryAssets.asset_id == new_asset.id,
                    ).first()
                    if already_linked is None:
                        self.session.add(EntryAssets(
                            entry_id=entry.id, asset_id=new_asset.id,
                            role=f"{ea.role}-{op}", position=(ea.position or 0) + 100,
                            metadata_json={"derived_from": str(src.id), "derivation": token},
                        ))
                    self.session.commit()   # each derivative is atomic
                    already.add((str(src.id), token))
                    summaries.append(f"{ea.role}: {token} → {new_asset.slug}")
                except Exception as e:  # noqa: BLE001 — best-effort per asset/token
                    self.session.rollback()
                    logger.warning("media: %s on %s failed: %s", token, getattr(src, "slug", "?"), e)

        return summaries
