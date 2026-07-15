"""
Slug resolver for {{SLUG}} references.

Resolution order (Secrets win on collision):
  1. Secret backend (encrypted, write-only)
  2. Workspace Variable (plain-text, readable)

Unresolved slugs are left unchanged so misconfiguration is visible in logs.
"""

import re

from pydantic import UUID4

from marvin.core.root_logger import get_logger

from .factory import get_secret_backend

logger = get_logger(__name__)

SLUG_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def _get_variable(slug: str, group_id: UUID4 | None) -> str | None:
    """Look up a workspace variable by slug."""
    if group_id is None:
        return None
    try:
        from marvin.db.db_setup import session_context
        from marvin.db.models.groups.variables import WorkspaceVariable
        from sqlalchemy import select, and_

        with session_context() as session:
            result = session.execute(
                select(WorkspaceVariable.value).where(
                    and_(
                        WorkspaceVariable.slug == slug,
                        WorkspaceVariable.group_id == group_id,
                    )
                )
            ).scalar_one_or_none()
            return result
    except Exception as e:
        logger.debug(f"Variable lookup failed for '{slug}': {e}")
        return None


def resolve(value: str, group_id: UUID4 | None = None) -> str:
    """Replace {{SLUG}} references. Secrets take priority over Variables."""
    if "{{" not in value:
        return value

    backend = get_secret_backend()

    def replacer(match: re.Match) -> str:
        slug = match.group(1)
        # 1. Try secrets first
        result = backend.get(slug, group_id)
        if result is not None:
            return result
        # 2. Fall back to variables
        result = _get_variable(slug, group_id)
        if result is not None:
            return result
        logger.warning(f"'{{{{ {slug} }}}}' not found as secret or variable for group {group_id}")
        return match.group(0)

    return SLUG_RE.sub(replacer, value)


def resolve_dict(data: dict[str, str], group_id: UUID4 | None = None) -> dict[str, str]:
    """Resolve {{SLUG}} in all dict values (e.g. webhook headers)."""
    return {key: resolve(val, group_id) for key, val in data.items()}
