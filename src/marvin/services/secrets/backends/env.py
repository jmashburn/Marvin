"""
Environment variable secret backend.

Reads secrets from server environment variables. Values are set by the
sysadmin (Docker secrets, Kubernetes secrets, Doppler, etc.) — Marvin
never writes to the environment. Zero storage, zero encryption overhead.

Slugs are resolved directly: {{MY_SECRET}} -> os.environ.get("MY_SECRET")
"""

import os

from pydantic import UUID4

from ..base import SecretBackend

ENV_PREFIX = "MARVIN_SECRET_"


class EnvSecretBackend(SecretBackend):
    """
    Read-only backend that resolves secrets from environment variables.

    Any env var is accessible by slug. Optionally, vars prefixed with
    MARVIN_SECRET_ are discoverable via list_slugs().
    """

    def get(self, slug: str, group_id: UUID4 | None = None) -> str | None:
        # Try the slug directly, then with the prefix
        return os.environ.get(slug) or os.environ.get(f"{ENV_PREFIX}{slug}")

    def set(self, slug: str, value: str, group_id: UUID4 | None = None) -> None:
        raise NotImplementedError(
            "EnvSecretBackend is read-only. Set secrets in your environment "
            "(Docker secrets, Kubernetes secrets, .env file, etc.)"
        )

    def delete(self, slug: str, group_id: UUID4 | None = None) -> None:
        raise NotImplementedError("EnvSecretBackend is read-only.")

    def list_slugs(self, group_id: UUID4 | None = None) -> list[str]:
        """Return slugs for env vars prefixed with MARVIN_SECRET_."""
        return [
            key[len(ENV_PREFIX):]
            for key in os.environ
            if key.startswith(ENV_PREFIX)
        ]
