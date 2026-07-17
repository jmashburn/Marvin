"""Pydantic schemas for AI executions."""

from datetime import datetime

from pydantic import UUID4, ConfigDict

from marvin.schemas._marvin import _MarvinModel


class AIExecutionRead(_MarvinModel):
    id: UUID4
    group_id: UUID4
    operation_slug: str
    provider_type: str
    model_id: str
    status: str
    triggered_by: UUID4 | None = None
    trigger_type: str
    entity_type: str | None = None
    entity_id: UUID4 | None = None
    output_json: dict | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None
    duration_ms: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIOperationExecuteRequest(_MarvinModel):
    entity_type: str | None = None
    entity_id: UUID4 | None = None
    input: dict = {}
    model_override: str | None = None  # override the workspace default model

    model_config = ConfigDict(from_attributes=True)


class AIReindexRequest(_MarvinModel):
    """Reindex embeddings for a single entity, or the whole workspace when scope='workspace'."""
    entity_type: str | None = None   # entry | resource
    entity_id: UUID4 | None = None
    scope: str | None = None         # "workspace" → reindex all entries + resources

    model_config = ConfigDict(from_attributes=True)
