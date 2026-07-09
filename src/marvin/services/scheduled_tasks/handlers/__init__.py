"""
Scheduled task handler system.

Handlers execute scheduled tasks and emit events. The TaskHandlerRegistry
maps task_type strings to handler classes for dynamic dispatch.
"""

from abc import ABC, abstractmethod
from typing import Type

from marvin.db.models.platform.scheduled_tasks import ScheduledTaskModel
from marvin.services.event_bus_service.event_bus_service import EventBusService


class ScheduledTaskHandler(ABC):
    """
    Base class for scheduled task handlers.

    Handlers implement the execute() method to perform work when a task is triggered.
    They should emit domain events via the EventBusService to notify other systems.
    """

    # Handler metadata (override in subclasses)
    name: str = ""
    """Human-readable name of this handler."""
    description: str = ""
    """Description of what this handler does."""
    config_schema: dict | None = None
    """JSON schema describing expected task_config fields."""

    @abstractmethod
    def execute(self, task: ScheduledTaskModel, event_bus: EventBusService) -> None:
        """
        Execute the scheduled task.

        Args:
            task: The scheduled task model with configuration
            event_bus: Event bus for emitting events

        Raises:
            Exception: Any exception will be caught by the scheduler and logged
        """
        pass


class TaskHandlerRegistry:
    """
    Registry mapping task_type to handler classes.

    Handlers register themselves at module import time via the @register decorator
    or explicit register() calls.
    """

    _handlers: dict[str, Type[ScheduledTaskHandler]] = {}

    @classmethod
    def register(cls, task_type: str, handler: Type[ScheduledTaskHandler]) -> None:
        """
        Register a handler for a task type.

        Args:
            task_type: Task type identifier (e.g., 'cleanup_temp_files')
            handler: Handler class to instantiate when task executes
        """
        cls._handlers[task_type] = handler

    @classmethod
    def get_handler(cls, task_type: str) -> ScheduledTaskHandler:
        """
        Get a handler instance for a task type.

        Args:
            task_type: Task type identifier

        Returns:
            Instantiated handler

        Raises:
            ValueError: If no handler is registered for this task type
        """
        handler_class = cls._handlers.get(task_type)
        if not handler_class:
            raise ValueError(f"No handler registered for task_type: {task_type}")
        return handler_class()

    @classmethod
    def is_registered(cls, task_type: str) -> bool:
        """Check if a handler is registered for a task type."""
        return task_type in cls._handlers

    @classmethod
    def list_registered_types(cls) -> list[str]:
        """Get list of all registered task types."""
        return list(cls._handlers.keys())

    @classmethod
    def get_task_type_info(cls) -> list[dict]:
        """
        Get metadata about all registered task types.

        Returns:
            List of dicts with task_type, name, description, and config_schema
        """
        info = []
        for task_type, handler_class in cls._handlers.items():
            handler_instance = handler_class()
            info.append(
                {
                    "task_type": task_type,
                    "name": handler_instance.name or task_type.replace("_", " ").title(),
                    "description": handler_instance.description or handler_class.__doc__ or "",
                    "config_schema": handler_instance.config_schema,
                }
            )
        return info


__all__ = [
    "ScheduledTaskHandler",
    "TaskHandlerRegistry",
]
