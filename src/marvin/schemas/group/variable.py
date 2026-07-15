"""Pydantic schemas for workspace variables."""

from pydantic import UUID4, ConfigDict, field_validator

from marvin.schemas._marvin import _MarvinModel


class WorkspaceVariableCreate(_MarvinModel):
    name: str
    slug: str
    description: str | None = None
    value: str

    @field_validator("slug")
    @classmethod
    def slug_uppercase(cls, v: str) -> str:
        return v.strip().upper().replace(" ", "_").replace("-", "_")


class WorkspaceVariableUpdate(_MarvinModel):
    name: str | None = None
    description: str | None = None
    value: str | None = None


class WorkspaceVariableRead(_MarvinModel):
    """Value IS included — variables are not secret."""

    id: UUID4
    group_id: UUID4
    name: str
    slug: str
    description: str | None = None
    value: str

    model_config = ConfigDict(from_attributes=True)
