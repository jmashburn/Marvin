"""
AI provider factory — mirrors get_secret_backend() / get_storage_provider().

get_ai_provider()              — instantiate a provider from type + credentials
get_workspace_ai_provider()   — resolve the active provider for a workspace
"""

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.core.config import get_app_settings

from .base import AIProvider


class AIDisabledError(Exception):
    """Raised when AI is disabled for a workspace or not configured."""


class AIConfigError(Exception):
    """Raised when AI provider configuration is invalid or incomplete."""


def get_ai_provider(
    provider_type: str,
    api_key: str | None = None,
    base_url: str | None = None,
    metadata: dict | None = None,
) -> AIProvider:
    """
    Return a configured AIProvider instance.

    Lazy imports keep unused provider SDKs out of the module graph.
    Mirrors get_secret_backend() — a simple switch on type string.
    """
    if provider_type == "openai":
        from .providers.openai import OpenAIProvider
        return OpenAIProvider(api_key=api_key or "", base_url=base_url)

    if provider_type == "anthropic":
        from .providers.anthropic import AnthropicProvider
        return AnthropicProvider(api_key=api_key or "")

    if provider_type == "google":
        from .providers.google import GoogleProvider
        return GoogleProvider(api_key=api_key or "")

    if provider_type == "azure":
        from .providers.azure import AzureOpenAIProvider
        api_version = (metadata or {}).get("api_version", "2024-02-01")
        return AzureOpenAIProvider(api_key=api_key or "", base_url=base_url or "", api_version=api_version)

    if provider_type == "ollama":
        from .providers.ollama import OllamaProvider
        return OllamaProvider(base_url=base_url or "http://localhost:11434")

    raise ValueError(f"Unknown AI provider type: {provider_type!r}")


def get_workspace_ai_provider(session: Session, group_id: UUID4) -> AIProvider:
    """
    Resolve the active provider for a workspace, honouring credential_mode.

    Resolution order (from workspace_ai_settings):
      platform  → AppSettings credentials
      workspace → active ai_providers row, key resolved via resolve_secret()
    """
    from marvin.db.models.groups.ai_providers import AIProviderModel
    from marvin.db.models.groups.ai_settings import WorkspaceAISettingsModel
    from marvin.services.secrets.resolver import resolve_secret

    settings = session.query(WorkspaceAISettingsModel).filter_by(group_id=group_id).first()

    if not settings or not settings.enabled:
        raise AIDisabledError(f"AI is disabled for workspace {group_id}")

    if settings.credential_mode == "platform":
        app = get_app_settings()
        provider_type = settings.provider or getattr(app, "AI_DEFAULT_PROVIDER", "openai")
        api_key = getattr(app, f"{provider_type.upper()}_API_KEY", None)
        base_url = getattr(app, f"{provider_type.upper()}_BASE_URL", None)
        return get_ai_provider(provider_type, api_key, base_url)

    if settings.credential_mode == "workspace":
        # Preferred: a full Providers row (supports base_url, api_version, multiple providers).
        provider_row = (
            session.query(AIProviderModel)
            .filter_by(group_id=group_id, is_default=True, enabled=True)
            .first()
        )
        if provider_row:
            api_key = resolve_secret(provider_row.secret_ref, group_id) if provider_row.secret_ref else None
            return get_ai_provider(
                provider_row.provider_type,
                api_key,
                provider_row.base_url,
                provider_row.metadata_json,
            )

        # Fallback: build from the simple AI Settings fields when no Providers row exists.
        # Covers key-only providers (OpenAI/Anthropic/Google); Ollama/Azure still need a
        # Providers row for base_url / api_version.
        if not settings.provider:
            raise AIConfigError(
                "No AI provider configured for this workspace. Set a provider and API-key "
                "secret in AI Settings, or add a provider under the Providers config."
            )
        api_key = resolve_secret(settings.secret_ref, group_id) if settings.secret_ref else None
        return get_ai_provider(settings.provider, api_key)

    raise AIDisabledError("No valid credential mode configured")
