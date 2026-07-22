"""Workspace integrations — credentialed connections to external services.

The provider *contract* (base classes, registry, dataclasses, http interface) lives in the standalone
``marvin_integration_sdk`` package so plugins can depend on it without pulling in core. This package
re-exports it for internal call sites, supplies the core ``http`` helper, and imports the built-in
providers so importing it populates the registry.
"""

from marvin_integration_sdk import (
    INTEGRATION_REGISTRY,
    CredentialField,
    HttpHelper,
    IntegrationContext,
    IntegrationProvider,
    PolledEvent,
    ProviderAction,
    ProviderEvent,
    Response,
    get_provider,
    list_providers,
    register_provider,
)

from . import providers  # noqa: F401 — importing registers the built-in providers
from .http_client import MarvinHttpHelper, build_http

__all__ = [
    "INTEGRATION_REGISTRY",
    "CredentialField",
    "ProviderEvent",
    "ProviderAction",
    "PolledEvent",
    "IntegrationContext",
    "IntegrationProvider",
    "HttpHelper",
    "Response",
    "register_provider",
    "get_provider",
    "list_providers",
    "MarvinHttpHelper",
    "build_http",
]
