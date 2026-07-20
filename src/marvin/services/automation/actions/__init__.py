"""Action executors for Flavor B automations.

Importing this package registers every executor (side-effect imports below). The engine calls
:func:`run_action` to dispatch by kind; :func:`available_kinds` drives the builder's options.
"""

from .base import ACTION_EXECUTORS, AutomationActionError, available_kinds, register_action, run_action

# Register executors (import for side effects).
from . import emit_event, entry, handler, operation, webhook  # noqa: E402,F401

__all__ = [
    "ACTION_EXECUTORS",
    "AutomationActionError",
    "available_kinds",
    "register_action",
    "run_action",
]
