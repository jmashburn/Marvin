"""
Secret slug resolver.

Replaces {{SLUG}} references in strings with values from the configured
secret backend. Unresolved slugs are left unchanged so issues are visible.
"""

import re

from pydantic import UUID4

from marvin.core.root_logger import get_logger

from .factory import get_secret_backend

logger = get_logger(__name__)

SECRET_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def resolve(value: str, group_id: UUID4 | None = None) -> str:
    """Replace {{SLUG}} references with secret values."""
    if "{{" not in value:
        return value

    backend = get_secret_backend()

    def replacer(match: re.Match) -> str:
        slug = match.group(1)
        secret = backend.get(slug, group_id)
        if secret is None:
            logger.warning(f"Secret '{{{{ {slug} }}}}' not found for group {group_id} — leaving unchanged")
            return match.group(0)
        return secret

    return SECRET_RE.sub(replacer, value)


def resolve_dict(data: dict[str, str], group_id: UUID4 | None = None) -> dict[str, str]:
    """Resolve {{SLUG}} references in all values of a dict (e.g. webhook headers)."""
    return {key: resolve(val, group_id) for key, val in data.items()}
