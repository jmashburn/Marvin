"""Workspace integrations — credentialed connections to external services.

Importing this package registers the built-in providers as a side effect, so anything
that reaches for the registry (the controller, the automation runner) gets a populated
INTEGRATION_REGISTRY.
"""

from . import providers  # noqa: F401 — registers built-in providers
from .base import (
    INTEGRATION_REGISTRY,
    CredentialField,
    IntegrationContext,
    IntegrationProvider,
    PolledEvent,
    ProviderAction,
    ProviderEvent,
    get_provider,
    list_providers,
    register_provider,
)

__all__ = [
    "INTEGRATION_REGISTRY",
    "CredentialField",
    "IntegrationContext",
    "IntegrationProvider",
    "PolledEvent",
    "ProviderAction",
    "ProviderEvent",
    "get_provider",
    "list_providers",
    "register_provider",
]
