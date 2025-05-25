"""
This module defines the `ScheduledFunc` Pydantic model, used to represent
a scheduled function or task within the Marvin application's scheduler system.

This model encapsulates all necessary information for the scheduler to manage
and execute a function at a predefined time or interval, including its identifier,
timing, callback, and execution parameters.
"""
from collections.abc import Callable # For type hinting callables
from dataclasses import dataclass, field # For creating dataclasses

from pydantic import BaseModel # Pydantic's BaseModel

# Note: The ScheduledFunc class uses `@dataclass(slots=True)` and also inherits from `pydantic.BaseModel`.
# While this is possible, it's an unconventional pattern. Pydantic models typically
# handle data validation and serialization, and dataclasses are for simpler data holding.
# Mixing them might lead to unexpected behavior with Pydantic's features if not carefully managed.
# For instance, Pydantic's validation might not fully apply to fields managed by dataclass defaults
# in the same way as pure Pydantic models, or vice-versa for dataclass features.
# However, Pydantic v2 has improved compatibility with dataclasses.


@dataclass(slots=True) # `slots=True` can provide memory optimization for many instances.
class ScheduledFunc(BaseModel): # Inheriting from Pydantic BaseModel for validation and serialization.
    """
    Represents a function or task scheduled for execution.

    This model holds the configuration for a scheduled job, including its unique ID,
    human-readable name, execution time (hour and minute), the callback function
    to execute, and other scheduling parameters like `max_instances` and arguments
    for the callback.
    """
    id: tuple[str, int] 
    """
    A unique identifier for the scheduled function, typically a tuple combining
    a string (e.g., job group or type) and an integer (e.g., specific ID within that group).
    Example: `("daily_task", 123)`
    """
    name: str
    """A human-readable name for the scheduled function, useful for logging and management."""
    hour: int
    """The hour (0-23) at which the function is scheduled to run."""
    minutes: int # Should be `minute` for consistency with `datetime.time` if that's the intent.
    """The minute (0-59) at which the function is scheduled to run."""
    callback: Callable[..., Any] # More specific Callable type if possible, e.g., Callable[[], None]
    """The actual function or method to be called when the schedule triggers."""

    max_instances: int = 1
    """
    The maximum number of concurrent instances of this job that are allowed to run.
    Defaults to 1, meaning if a job is still running when its next schedule triggers,
    the new run will be skipped.
    """
    replace_existing: bool = True
    """
    If True, adding a job with an existing ID will replace the old job.
    If False, it might raise an error or be ignored. Defaults to True.
    """
    args: list[Any] = field(default_factory=list) # Using Any for args elements for flexibility
    """
    A list of positional arguments to pass to the `callback` function when it's executed.
    Defaults to an empty list.
    """
    # Potential future fields:
    # kwargs: dict[str, Any] = field(default_factory=dict) # For keyword arguments
    # run_once: bool = False # If True, job runs once then removes itself
    # timezone: str | None = None # To specify timezone for hour/minute
