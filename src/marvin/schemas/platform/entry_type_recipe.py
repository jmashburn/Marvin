"""Entry type authoring recipe.

Where `schema_json` defines the *fields* (the form) and `capabilities_json`/`rendering_json`
define *output* behaviour/render, `recipe_json` defines the *authoring* contract — what to
gather and derive to build an entry of this type:

- assets: how many images, per-role limits (hero/gallery/thumbnail), what to derive from each
- resources: entities to extract from content into linked resources (e.g. suppliers)
- enrichment: AI/media steps the recipe runs on compose

v1 is intentionally permissive (extra fields allowed) while the shape settles. Roles use the
same vocabulary the renderer already reads (hero/featured/gallery/thumbnail).
"""

from pydantic import ConfigDict, Field

from marvin.schemas._marvin import _MarvinModel


class RecipeAssetRole(_MarvinModel):
    """A named image slot for the entry type (e.g. hero, gallery, thumbnail)."""

    role: str
    min: int = 0
    max: int | None = None
    required: bool = False
    derive: list[str] = Field(default_factory=list, description="thumbnail | palette | enhance | …")

    model_config = ConfigDict(extra="allow")


class RecipeAssets(_MarvinModel):
    """Overall asset contract for the entry type."""

    min: int = 0
    max: int | None = None
    roles: list[RecipeAssetRole] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class RecipeResourceExtract(_MarvinModel):
    """Pull named entities out of a content field into linked resources."""

    type: str                      # supplier | tool | reference | …
    source: str = "body"           # which field to read entities from
    capture: list[str] = Field(default_factory=list, description="name | url | notes | …")

    model_config = ConfigDict(extra="allow")


class RecipeResources(_MarvinModel):
    extract: list[RecipeResourceExtract] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class EntryTypeRecipe(_MarvinModel):
    """Authoring recipe for an entry type (stored in entry_types.recipe_json)."""

    assets: RecipeAssets | None = None
    resources: RecipeResources | None = None
    enrichment: dict | None = None

    model_config = ConfigDict(extra="allow")
