"""
Database secret backend.

Stores secrets in the workspace_secrets table, encrypted at rest using
Fernet symmetric encryption. The encryption key is derived from
settings.SECRET (the per-installation secret stored in DATA_DIR/.secret).
"""

import base64
import hashlib

from pydantic import UUID4

from marvin.core.config import get_app_settings
from marvin.core.root_logger import get_logger
from marvin.db.db_setup import session_context

from ..base import SecretBackend

logger = get_logger(__name__)


def _get_fernet():
    """Build a Fernet instance from the installation secret."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise RuntimeError(
            "The 'cryptography' package is required for the database secret backend. "
            "Install it: pip install cryptography"
        )
    settings = get_app_settings()
    raw = settings.SECRET.encode() if isinstance(settings.SECRET, str) else settings.SECRET
    # Derive a 32-byte key via SHA-256, then base64url-encode for Fernet
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


class DatabaseSecretBackend(SecretBackend):
    """Fernet-encrypted secrets stored in the workspace_secrets DB table."""

    def get(self, slug: str, group_id: UUID4 | None = None) -> str | None:
        from marvin.db.models.groups.secrets import WorkspaceSecret
        from sqlalchemy import select, and_

        with session_context() as session:
            stmt = select(WorkspaceSecret).where(
                and_(
                    WorkspaceSecret.slug == slug,
                    WorkspaceSecret.group_id == group_id,
                )
            )
            secret = session.execute(stmt).scalar_one_or_none()
            if secret is None:
                return None
            try:
                return _get_fernet().decrypt(secret.encrypted_value.encode()).decode()
            except Exception:
                logger.error(f"Failed to decrypt secret '{slug}' for group {group_id}")
                return None

    def set(self, slug: str, value: str, group_id: UUID4 | None = None) -> None:
        from marvin.db.models.groups.secrets import WorkspaceSecret
        from sqlalchemy import select, and_

        encrypted = _get_fernet().encrypt(value.encode()).decode()

        with session_context() as session:
            stmt = select(WorkspaceSecret).where(
                and_(
                    WorkspaceSecret.slug == slug,
                    WorkspaceSecret.group_id == group_id,
                )
            )
            existing = session.execute(stmt).scalar_one_or_none()
            if existing:
                existing.encrypted_value = encrypted
            else:
                secret = WorkspaceSecret(
                    session=session,
                    group_id=group_id,
                    slug=slug,
                    name=slug,
                    encrypted_value=encrypted,
                )
                session.add(secret)
            session.commit()

    def delete(self, slug: str, group_id: UUID4 | None = None) -> None:
        from marvin.db.models.groups.secrets import WorkspaceSecret
        from sqlalchemy import select, and_

        with session_context() as session:
            stmt = select(WorkspaceSecret).where(
                and_(
                    WorkspaceSecret.slug == slug,
                    WorkspaceSecret.group_id == group_id,
                )
            )
            secret = session.execute(stmt).scalar_one_or_none()
            if secret:
                session.delete(secret)
                session.commit()

    def list_slugs(self, group_id: UUID4 | None = None) -> list[str]:
        from marvin.db.models.groups.secrets import WorkspaceSecret
        from sqlalchemy import select

        with session_context() as session:
            stmt = select(WorkspaceSecret.slug).where(
                WorkspaceSecret.group_id == group_id
            )
            return list(session.execute(stmt).scalars().all())
