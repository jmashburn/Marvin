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


__all__ = [
    "ScheduledTaskHandler",
    "TaskHandlerRegistry",
]
