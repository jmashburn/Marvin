"""Pydantic schemas for workspace secrets."""

import datetime

from pydantic import UUID4, ConfigDict, field_validator

from marvin.schemas._marvin import _MarvinModel


class WorkspaceSecretCreate(_MarvinModel):
    """Create a new workspace secret. Value is plaintext — encrypted on write."""

    name: str
    slug: str
    description: str | None = None
    value: str

    @field_validator("slug")
    @classmethod
    def slug_uppercase(cls, v: str) -> str:
        return v.strip().upper().replace(" ", "_").replace("-", "_")


class WorkspaceSecretUpdate(_MarvinModel):
    """Update a workspace secret. Omit value to keep the existing one."""

    name: str | None = None
    description: str | None = None
    value: str | None = None

    @field_validator("slug", mode="before", check_fields=False)
    @classmethod
    def slug_uppercase(cls, v: str) -> str:
        return v.strip().upper().replace(" ", "_").replace("-", "_")


class WorkspaceSecretRead(_MarvinModel):
    """Read schema — value is intentionally excluded (write-only like GitHub Secrets)."""

    id: UUID4
    group_id: UUID4
    name: str
    slug: str
    description: str | None = None
    created_at: datetime.datetime | None = None
    update_at: datetime.datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceSecretWithValue(WorkspaceSecretRead):
    """Includes decrypted value — only returned by the /reveal endpoint."""

    value: str
