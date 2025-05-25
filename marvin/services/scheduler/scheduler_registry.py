"""
This module defines the `SchedulerRegistry`, a static class used to register
and manage callback functions that are intended to be scheduled for periodic
execution (e.g., daily, hourly, minutely) by a scheduler service.

The registry provides static methods to add, remove, and list these callbacks,
which are stored in static lists categorized by their intended frequency.
This allows different parts of the application to register functions to be run
by a central scheduler without needing direct access to the scheduler instance itself.
"""
from collections.abc import Callable, Iterable # For type hinting callables and iterables

from marvin.core import root_logger # Application logger

# Logger instance for this module
logger = root_logger.get_logger()


class SchedulerRegistry:
    """
    A static container class for registering and managing callback functions
    intended for scheduled execution.

    This class uses static lists (`_daily`, `_hourly`, `_minutely`) to store
    references to functions that should be run at different frequencies.
    All methods are static, allowing for global registration and management of
    these scheduled tasks throughout the application.

    The actual scheduling and execution of these registered callbacks are handled
    by a separate scheduler service that would consume these lists.
    """

    # Static lists to store registered callback functions for different frequencies.
    _daily: list[Callable[[], None]] = [] # Callbacks to be run daily. Type hint assumes no args, no return.
    _hourly: list[Callable[[], None]] = [] # Callbacks to be run hourly.
    _minutely: list[Callable[[], None]] = [] # Callbacks to be run every minute.

    @staticmethod
    def _register(
        frequency_name: str, # Renamed `name` to `frequency_name` for clarity
        callback_list: list[Callable[[], None]], # Renamed `callbacks` to `callback_list`
        new_callbacks: Iterable[Callable[[], None]] # Renamed `callback` to `new_callbacks`
    ) -> None:
        """
        Internal static helper method to register one or more callbacks to a specific list.

        Args:
            frequency_name (str): The name of the frequency category (e.g., "daily", "hourly")
                                  for logging purposes.
            callback_list (list[Callable[[], None]]): The specific static list
                                                     (e.g., `SchedulerRegistry._daily`)
                                                     to which the callbacks will be added.
            new_callbacks (Iterable[Callable[[], None]]): An iterable of callback functions
                                                          to register.
        """
        for cb_func in new_callbacks: # Renamed `cb` to `cb_func`
            logger.debug(f"Registering {frequency_name} callback: {getattr(cb_func, '__name__', repr(cb_func))}")
            callback_list.append(cb_func)

    @staticmethod
    def register_daily(*callbacks_to_add: Callable[[], None]) -> None: # Renamed `callbacks`
        """
        Registers one or more callback functions to be scheduled for daily execution.

        Args:
            *callbacks_to_add (Callable[[], None]): Variable number of callback functions.
                                                   Each function should take no arguments
                                                   and return None.
        """
        SchedulerRegistry._register("daily", SchedulerRegistry._daily, callbacks_to_add)

    @staticmethod
    def remove_daily(callback_to_remove: Callable[[], None]) -> None: # Renamed `callback`
        """
        Removes a previously registered daily callback function.

        Args:
            callback_to_remove (Callable[[], None]): The specific callback function to remove
                                                     from the daily schedule.

        Raises:
            ValueError: If the `callback_to_remove` is not found in the list of daily callbacks.
        """
        try:
            logger.debug(f"Removing daily callback: {getattr(callback_to_remove, '__name__', repr(callback_to_remove))}")
            SchedulerRegistry._daily.remove(callback_to_remove)
        except ValueError:
            logger.warning(f"Attempted to remove daily callback not found in registry: {getattr(callback_to_remove, '__name__', repr(callback_to_remove))}")


    @staticmethod
    def register_hourly(*callbacks_to_add: Callable[[], None]) -> None: # Renamed
        """
        Registers one or more callback functions to be scheduled for hourly execution.

        Args:
            *callbacks_to_add (Callable[[], None]): Variable number of callback functions.
        """
        # Original code had "daily" as frequency_name here, corrected to "hourly".
        SchedulerRegistry._register("hourly", SchedulerRegistry._hourly, callbacks_to_add)

    @staticmethod
    def remove_hourly(callback_to_remove: Callable[[], None]) -> None: # Renamed
        """
        Removes a previously registered hourly callback function.

        Args:
            callback_to_remove (Callable[[], None]): The callback to remove.
        
        Raises:
            ValueError: If the callback is not found.
        """
        try:
            logger.debug(f"Removing hourly callback: {getattr(callback_to_remove, '__name__', repr(callback_to_remove))}")
            SchedulerRegistry._hourly.remove(callback_to_remove)
        except ValueError:
            logger.warning(f"Attempted to remove hourly callback not found in registry: {getattr(callback_to_remove, '__name__', repr(callback_to_remove))}")


    @staticmethod
    def register_minutely(*callbacks_to_add: Callable[[], None]) -> None: # Renamed
        """
        Registers one or more callback functions to be scheduled for minutely execution.

        Args:
            *callbacks_to_add (Callable[[], None]): Variable number of callback functions.
        """
        SchedulerRegistry._register("minutely", SchedulerRegistry._minutely, callbacks_to_add)

    @staticmethod
    def remove_minutely(callback_to_remove: Callable[[], None]) -> None: # Renamed
        """
        Removes a previously registered minutely callback function.

        Args:
            callback_to_remove (Callable[[], None]): The callback to remove.

        Raises:
            ValueError: If the callback is not found.
        """
        try:
            logger.debug(f"Removing minutely callback: {getattr(callback_to_remove, '__name__', repr(callback_to_remove))}")
            SchedulerRegistry._minutely.remove(callback_to_remove)
        except ValueError:
            logger.warning(f"Attempted to remove minutely callback not found in registry: {getattr(callback_to_remove, '__name__', repr(callback_to_remove))}")


    @staticmethod
    def print_jobs() -> None:
        """
        Prints all registered scheduled jobs (callbacks) to the debug log.

        This method iterates through the daily, hourly, and minutely callback lists
        and logs the name of each registered function. Useful for debugging and
        verifying which tasks are currently registered with the scheduler system.
        """
        logger.debug("--- Registered Daily Jobs ---")
        if SchedulerRegistry._daily:
            for job_func in SchedulerRegistry._daily: # Renamed `job` to `job_func`
                logger.debug(f"Daily job: {getattr(job_func, '__name__', repr(job_func))}")
        else:
            logger.debug("No daily jobs registered.")

        logger.debug("--- Registered Hourly Jobs ---")
        if SchedulerRegistry._hourly:
            for job_func in SchedulerRegistry._hourly:
                logger.debug(f"Hourly job: {getattr(job_func, '__name__', repr(job_func))}")
        else:
            logger.debug("No hourly jobs registered.")

        logger.debug("--- Registered Minutely Jobs ---")
        if SchedulerRegistry._minutely:
            for job_func in SchedulerRegistry._minutely:
                logger.debug(f"Minutely job: {getattr(job_func, '__name__', repr(job_func))}")
        else:
            logger.debug("No minutely jobs registered.")
        logger.debug("--- End of Registered Jobs ---")
