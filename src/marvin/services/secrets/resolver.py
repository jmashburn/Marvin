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


def resolve(value: str, group_id: UUID4 | None = None, allow_secrets: bool = True) -> str:
    """
    Replace {{SLUG}} references with resolved values.

    Resolution order (when allow_secrets=True):
      1. Secrets (encrypted, wins on collision)
      2. Variables (plain-text fallback)

    Use allow_secrets=False for email template content — secret values
    should never appear in email bodies/subjects visible to recipients.
    Use allow_secrets=True (default) for webhook headers and transport config
    where credentials are needed.
    """
    if "{{" not in value:
        return value

    backend = get_secret_backend()

    def replacer(match: re.Match) -> str:
        slug = match.group(1)
        # 1. Try secrets (only when permitted by context)
        if allow_secrets:
            result = backend.get(slug, group_id)
            if result is not None:
                return result
        # 2. Fall back to variables
        result = _get_variable(slug, group_id)
        if result is not None:
            return result
        logger.warning(f"'{{{{ {slug} }}}}' not resolved for group {group_id} (allow_secrets={allow_secrets})")
        return match.group(0)

    return SLUG_RE.sub(replacer, value)


def resolve_dict(data: dict[str, str], group_id: UUID4 | None = None, allow_secrets: bool = True) -> dict[str, str]:
    """Resolve {{SLUG}} in all dict values (e.g. webhook headers)."""
    return {key: resolve(val, group_id, allow_secrets=allow_secrets) for key, val in data.items()}


def resolve_secret(slug: str, group_id: UUID4 | None = None) -> str | None:
    """
    Resolve a single slug as a Secret only — for infrastructure config
    (e.g. Gmail OAuth token, SMTP password) not template content.
    Returns None if not found.
    """
    return get_secret_backend().get(slug, group_id)
