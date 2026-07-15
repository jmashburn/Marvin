"""Abstract base class for secret backends."""

from abc import ABC, abstractmethod

from pydantic import UUID4


class SecretBackend(ABC):
    """
    Pluggable secret storage backend.

    Implementations: database, disk, env, vault, bitwarden.
    Selected via settings.SECRET_BACKEND.
    """

    @abstractmethod
    def get(self, slug: str, group_id: UUID4 | None = None) -> str | None:
        """Return the secret value for slug, or None if not found."""
        ...

    @abstractmethod
    def set(self, slug: str, value: str, group_id: UUID4 | None = None) -> None:
        """Store or overwrite a secret value."""
        ...

    @abstractmethod
    def delete(self, slug: str, group_id: UUID4 | None = None) -> None:
        """Remove a secret."""
        ...

    @abstractmethod
    def list_slugs(self, group_id: UUID4 | None = None) -> list[str]:
        """Return all slugs accessible for this group."""
        ...
