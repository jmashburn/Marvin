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

from .http_client import MarvinHttpHelper, build_http
from .loader import ProviderLoadReport, load_providers

# Discover built-in + installed-plugin providers once, at import time.
load_providers()


def load_reports() -> list[ProviderLoadReport]:
    """The per-source provider load reports (built-ins + installed plugins)."""
    return load_providers()


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
    "ProviderLoadReport",
    "load_providers",
    "load_reports",
]
