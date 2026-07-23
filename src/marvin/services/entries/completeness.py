"""Entry completeness contract.

One evaluator that answers "is this entry complete for its type?" from the type's
schema (required fields) + recipe (required assets, resource extracts, tags). It is the
single source the publish gate uses to BLOCK on missing-required, and that AI authoring
uses to WARN so compose/revise can self-correct. Non-required gaps are always warnings,
never blockers — so "required on anything" (field, asset role, resource type, tags) is
declared in the type and enforced here, uniformly, for AI / Chat / backend publishing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from marvin.schemas.platform.entry_type_recipe import EntryTypeRecipe
from marvin.schemas.platform.entry_type_schema import EntryTypeSchemaDefinition

logger = logging.getLogger(__name__)

# Values that count as "not filled in".
_EMPTY: tuple = (None, "", [], {})


@dataclass
class CompletenessIssue:
    kind: str  # "field" | "asset" | "resource" | "tag"
    key: str  # field key / asset role / resource type / "*"
    message: str
    blocking: bool


@dataclass
class CompletenessReport:
    blocking: list[CompletenessIssue] = field(default_factory=list)
    warnings: list[CompletenessIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when nothing required is missing (optional gaps don't count)."""
        return not self.blocking

    def blocking_messages(self) -> list[str]:
        return [i.message for i in self.blocking]

    def warning_messages(self) -> list[str]:
        return [i.message for i in self.warnings]


def parse_schema(schema_json: dict | None) -> EntryTypeSchemaDefinition | None:
    if not schema_json:
        return None
    try:
        return EntryTypeSchemaDefinition.model_validate(schema_json)
    except Exception as e:  # noqa: BLE001 — a malformed schema must not break publishing
        logger.warning("completeness: could not parse schema_json: %s", e)
        return None


def parse_recipe(recipe_json: dict | None) -> EntryTypeRecipe | None:
    if not recipe_json:
        return None
    try:
        return EntryTypeRecipe.model_validate(recipe_json)
    except Exception as e:  # noqa: BLE001
        logger.warning("completeness: could not parse recipe_json: %s", e)
        return None


def evaluate_completeness(
    *,
    schema: EntryTypeSchemaDefinition | None,
    recipe: EntryTypeRecipe | None,
    data_json: dict | None,
    title: str | None = None,
    asset_roles: list[str] | None = None,
    resource_types: list[str] | None = None,
    tags: list[str] | None = None,
) -> CompletenessReport:
    """Evaluate an entry's state against its type's contract.

    All inputs are primitives so the same evaluator serves the publish gate (state from a
    persisted entry) and AI authoring (state from a freshly-composed draft).
    """
    data = data_json or {}
    asset_roles = asset_roles or []
    resource_types = resource_types or []
    tags = tags or []
    report = CompletenessReport()

    def add(kind: str, key: str, message: str, blocking: bool) -> None:
        (report.blocking if blocking else report.warnings).append(CompletenessIssue(kind=kind, key=key, message=message, blocking=blocking))

    # Title is the entry's identity — always required.
    if not (title or "").strip():
        add("field", "title", "Title is required.", True)

    # ── Fields (schema): required → block, optional-but-empty → warn ──────────
    if schema:
        for f in schema.fields:
            if getattr(f, "read_only", False):
                continue
            present = data.get(f.key) not in _EMPTY
            if getattr(f, "required", False):
                if not present:
                    add("field", f.key, f"Required field '{f.label}' is empty.", True)
            elif not present:
                add("field", f.key, f"Optional field '{f.label}' is empty.", False)

    # ── Assets (recipe): per-role minimums + overall minimum ─────────────────
    if recipe and getattr(recipe, "assets", None):
        counts: dict[str, int] = {}
        for r in asset_roles:
            counts[r] = counts.get(r, 0) + 1
        total = len(asset_roles)

        overall_min = getattr(recipe.assets, "min", 0) or 0
        if total < overall_min:
            add("asset", "*", f"Needs at least {overall_min} image(s); has {total}.", True)

        for role in recipe.assets.roles or []:
            role_min = getattr(role, "min", 0) or 0
            need = role_min if role_min else (1 if getattr(role, "required", False) else 0)
            if need <= 0:
                continue
            have = counts.get(role.role, 0)
            if have < need:
                add("asset", role.role, f"Needs {need} '{role.role}' image(s); has {have}.", True)

    # ── Resources (recipe.extract): required resource types ──────────────────
    if recipe and getattr(recipe, "resources", None):
        counts = {}
        for t in resource_types:
            counts[t] = counts.get(t, 0) + 1
        for ex in recipe.resources.extract or []:
            ex_min = getattr(ex, "min", 0) or 0
            need = ex_min if ex_min else (1 if getattr(ex, "required", False) else 0)
            if need <= 0:
                continue
            have = counts.get(ex.type, 0)
            if have < need:
                add("resource", ex.type, f"Needs {need} '{ex.type}' resource(s); has {have}.", True)

    # ── Tags (recipe.tags) ───────────────────────────────────────────────────
    tags_rule = getattr(recipe, "tags", None) if recipe else None
    if tags_rule:
        tag_min = getattr(tags_rule, "min", 0) or 0
        need = tag_min if tag_min else (1 if getattr(tags_rule, "required", False) else 0)
        if need > 0 and len(tags) < need:
            add("tag", "*", f"Needs at least {need} tag(s); has {len(tags)}.", True)

    return report


def evaluate_entry(entry, entry_type, *, data_json=None, title=None) -> CompletenessReport:
    """Evaluate a persisted ORM entry against its type. `data_json`/`title` override the
    entry's stored values so a pending update can be projected before it's applied."""
    schema = parse_schema(getattr(entry_type, "schema_json", None)) if entry_type else None
    recipe = parse_recipe(getattr(entry_type, "recipe_json", None)) if entry_type else None
    asset_roles = [ea.role for ea in getattr(entry, "entry_assets", []) or [] if getattr(ea, "role", None)]
    resource_types = [r.resource_type for r in getattr(entry, "resources", []) or []]
    tags = list(getattr(entry, "tag_names", []) or [])
    return evaluate_completeness(
        schema=schema,
        recipe=recipe,
        data_json=data_json if data_json is not None else getattr(entry, "data_json", None),
        title=title if title is not None else getattr(entry, "title", None),
        asset_roles=asset_roles,
        resource_types=resource_types,
        tags=tags,
    )
