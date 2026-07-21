"""Schemas for workspace integrations — credentialed connections to external services."""

from datetime import datetime

from pydantic import UUID4, Field, SecretStr

from marvin.schemas._marvin import _MarvinModel


class IntegrationCreate(_MarvinModel):
    """Create a new integration instance."""

    provider: str  # registry key, e.g. "vercel_deploy"
    name: str  # user-facing label
    slug: str | None = None  # derived from name if omitted
    config: dict = Field(default_factory=dict)
    credential: SecretStr | None = None  # write-only; stored via the secret backend, never read back


class IntegrationUpdate(_MarvinModel):
    """Patch an integration. A present `credential` rotates the stored secret."""

    name: str | None = None
    enabled: bool | None = None
    config: dict | None = None
    credential: SecretStr | None = None


class IntegrationRead(_MarvinModel):
    """An integration as returned by the API. Never carries the credential value."""

    id: UUID4
    provider: str
    name: str
    slug: str
    enabled: bool
    config: dict | None = None
    has_credential: bool = False  # whether a secret_ref is set — not the value
    status: str
    last_checked_at: datetime | None = None
    last_error: str | None = None


class IntegrationActionResult(_MarvinModel):
    """Result of running (or test-firing) a provider action."""

    ok: bool
    result: dict = Field(default_factory=dict)


class IntegrationCheckResult(_MarvinModel):
    """Result of a health check."""

    status: str
    last_error: str | None = None
    last_checked_at: datetime | None = None
