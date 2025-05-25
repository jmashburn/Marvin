"""
This module provides a utility decorator, `repeat_every`, for scheduling
functions to be executed periodically. The code is adapted/copied from the
`fastapi-utils` project by dmontagu.

(Source: https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/tasks.py)

The `repeat_every` decorator allows both synchronous and asynchronous functions
to be run repeatedly at a specified interval (in minutes), with options for
logging, exception handling, and limiting the number of repetitions. This is
useful for background tasks, cron-like jobs, or any operation that needs to
occur on a regular schedule within an asyncio application.

Note: This code is subject to the MIT license of the original `fastapi-utils` project.
"""

import asyncio
import logging
from asyncio import ensure_future # For scheduling the repeating task in the event loop
from collections.abc import Callable, Coroutine # For type hinting callables
from functools import wraps # For preserving function metadata when decorating
from traceback import format_exception # For formatting exception tracebacks for logging
from typing import Any # For generic type hints

from starlette.concurrency import run_in_threadpool # For running sync functions in a separate thread

# Type hints for callables that take no arguments and return None
NoArgsNoReturnFuncT = Callable[[], None] # Synchronous version
NoArgsNoReturnAsyncFuncT = Callable[[], Coroutine[Any, Any, None]] # Asynchronous version
# Type hint for the decorator itself
NoArgsNoReturnDecorator = Callable[[NoArgsNoReturnFuncT | NoArgsNoReturnAsyncFuncT], NoArgsNoReturnAsyncFuncT]


def repeat_every(
    *, # Keyword-only arguments
    minutes: float, # Changed from `seconds` in original fastapi-utils to `minutes` as per Marvin's usage
    wait_first: bool = False,
    logger: logging.Logger | None = None,
    raise_exceptions: bool = False,
    max_repetitions: int | None = None,
) -> NoArgsNoReturnDecorator:
    """
    Returns a decorator that modifies a function to be periodically re-executed.

    The decorated function should accept no arguments and return nothing. If arguments
    or a return value are needed, `functools.partial` or a wrapper function can be
    used before applying this decorator.

    Args:
        minutes (float): The number of minutes to wait between repeated calls.
        wait_first (bool, optional): If True, the function will wait for the initial
            `minutes` interval before the first execution. Defaults to False.
        logger (logging.Logger | None, optional): A logger instance to log exceptions
            raised by the decorated function. If None, exceptions are not logged by
            this decorator (though they might be handled by the asyncio event loop).
            Defaults to None.
        raise_exceptions (bool, optional): If True, exceptions from the decorated
            function will propagate and potentially stop the repeating execution.
            If False, exceptions are logged (if a logger is provided) and the
            execution continues to repeat. Defaults to False.
        max_repetitions (int | None, optional): The maximum number of times the
            function will be executed. If None, the function repeats indefinitely.
            Defaults to None.

    Returns:
        NoArgsNoReturnDecorator: A decorator that can be applied to a synchronous or
                                 asynchronous function.
    """

    def decorator(func: NoArgsNoReturnAsyncFuncT | NoArgsNoReturnFuncT) -> NoArgsNoReturnAsyncFuncT:
        """
        Inner decorator that wraps the function to enable periodic execution.
        It handles both synchronous and asynchronous functions.
        """
        # Check if the decorated function is a coroutine function (async def)
        is_coroutine = asyncio.iscoroutinefunction(func)

        @wraps(func) # Preserve original function's metadata (name, docstring, etc.)
        async def wrapped() -> None:
            """
            The wrapped function that will be called by the scheduler or application startup.
            It schedules the main `loop` to run in the asyncio event loop.
            """
            repetition_count = 0 # Counter for number of executions

            async def loop() -> None:
                """
                The core async loop that handles repeated execution, waiting, and error handling.
                """
                nonlocal repetition_count # Allow modification of outer scope's counter
                
                # If wait_first is True, pause for the specified interval before the first run
                if wait_first:
                    await asyncio.sleep(minutes * 60) # Convert minutes to seconds for sleep

                # Loop indefinitely or until max_repetitions is reached
                while max_repetitions is None or repetition_count < max_repetitions:
                    try:
                        if is_coroutine:
                            # If the original function is async, await it
                            await cast(NoArgsNoReturnAsyncFuncT, func)() # Cast for type checker
                        else:
                            # If the original function is sync, run it in a thread pool
                            # to avoid blocking the asyncio event loop.
                            await run_in_threadpool(cast(NoArgsNoReturnFuncT, func))
                        repetition_count += 1
                    except Exception as exc:
                        # Handle exceptions raised by the decorated function
                        if logger is not None:
                            # Format the exception traceback and log it
                            exception_details = "".join(format_exception(type(exc), exc, exc.__traceback__))
                            logger.error(f"Exception in scheduled task '{func.__name__}':\n{exception_details}")
                        if raise_exceptions:
                            # If raise_exceptions is True, re-raise the exception.
                            # This will typically stop the loop and might be handled by
                            # the asyncio loop's exception handler or a higher-level try-except.
                            raise exc 
                    
                    # Wait for the specified interval before the next repetition
                    await asyncio.sleep(minutes * 60) # Convert minutes to seconds

            # Schedule the loop to run in the asyncio event loop without awaiting its completion here.
            # This allows `wrapped` to return quickly, and the loop runs in the background.
            ensure_future(loop())

        return wrapped # Return the new async wrapped function

    return decorator # Return the actual decorator
