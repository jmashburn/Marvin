"""
Scheduled tasks service.

This module provides the infrastructure for executing scheduled tasks on a recurring
or one-time basis. Handlers are registered at import time and executed by the
SchedulerService when tasks are due.
"""

# Import handler modules to trigger registration
from .handlers import ScheduledTaskHandler, TaskHandlerRegistry

# Import all handler modules to register them
from .handlers import ai, automation, maintenance, publishing  # noqa: F401  — imported for handler registration side effects

__all__ = [
    "ScheduledTaskHandler",
    "TaskHandlerRegistry",
]
