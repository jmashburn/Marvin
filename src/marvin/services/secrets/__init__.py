"""Workspace Secrets — pluggable secret backend system."""

from .factory import get_secret_backend
from .base import SecretBackend

__all__ = ["get_secret_backend", "SecretBackend"]
