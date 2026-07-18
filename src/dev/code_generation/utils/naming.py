"""Naming utilities for code generation."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityNames:
    """All naming variants derived from a single entity name."""

    snake_singular: str
    snake_plural: str
    pascal_singular: str
    pascal_plural: str
    kebab_plural: str

    @property
    def route_prefix(self) -> str:
        return f"/{self.kebab_plural}"

    @property
    def table_name(self) -> str:
        return self.snake_plural


def _pluralize(word: str) -> str:
    if word.endswith(("sh", "ch", "x", "s", "z")):
        return word + "es"
    if word.endswith("y") and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


def _to_pascal(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def _to_kebab(snake: str) -> str:
    return snake.replace("_", "-")


def derive_names(entity: str, plural_override: str | None = None) -> EntityNames:
    normalized = re.sub(r"[^a-z0-9_]", "_", entity.lower().strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")

    if not normalized or not normalized.isidentifier():
        raise ValueError(f"'{entity}' is not a valid Python identifier after normalization")

    plural = plural_override or _pluralize(normalized)

    return EntityNames(
        snake_singular=normalized,
        snake_plural=plural,
        pascal_singular=_to_pascal(normalized),
        pascal_plural=_to_pascal(plural),
        kebab_plural=_to_kebab(plural),
    )
