"""Pydantic schemas for AI providers and models."""

from pydantic import UUID4, ConfigDict

from marvin.schemas._marvin import _MarvinModel


# ── Models ─────────────────────────────────────────────────────────────────

class AIModelCreate(_MarvinModel):
    name: str
    model_id: str
    is_default: bool = False
    context_window: int | None = None
    max_output_tokens: int | None = None
    supports_vision: bool = False
    supports_tools: bool = False
    enabled: bool = True

    model_config = ConfigDict(from_attributes=True)


class AIModelUpdate(_MarvinModel):
    name: str | None = None
    model_id: str | None = None
    is_default: bool | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    supports_vision: bool | None = None
    supports_tools: bool | None = None
    enabled: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class AIModelRead(AIModelCreate):
    id: UUID4
    provider_id: UUID4
    group_id: UUID4

    model_config = ConfigDict(from_attributes=True)


# ── Providers ───────────────────────────────────────────────────────────────

class AIProviderCreate(_MarvinModel):
    name: str
    slug: str
    provider_type: str  # openai | anthropic | google | azure | ollama | custom
    secret_ref: str | None = None
    base_url: str | None = None
    enabled: bool = True
    is_default: bool = False
    metadata_json: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class AIProviderUpdate(_MarvinModel):
    name: str | None = None
    slug: str | None = None
    provider_type: str | None = None
    secret_ref: str | None = None
    base_url: str | None = None
    enabled: bool | None = None
    is_default: bool | None = None
    metadata_json: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class AIProviderRead(AIProviderCreate):
    id: UUID4
    group_id: UUID4
    models: list[AIModelRead] = []

    model_config = ConfigDict(from_attributes=True)


class AIProviderTestResult(_MarvinModel):
    success: bool
    message: str
    available_models: list[str] = []

    model_config = ConfigDict(from_attributes=True)
