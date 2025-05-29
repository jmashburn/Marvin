"""
This module provides helper functions for safely calling functions with dynamic arguments.

It includes utilities to:
- Determine valid arguments for a given function.
- Check if a function accepts arbitrary keyword arguments (`**kwargs`).
- Safely call a function by providing only its valid arguments from a larger
  dictionary of potential arguments. This is particularly useful when initializing
  objects or calling functions where the input data might contain extra keys
  that are not part of the function's signature.
"""

import inspect
from collections.abc import Callable
from typing import Any


def get_valid_call(func: Callable, args_dict) -> dict:
    """
    Returns a dictionary of valid arguments for the supplied function. if kwargs are accepted,
    the original dictionary will be returned.
    """

    def get_valid_args(func: Callable) -> list[str]:
        """
        Returns a tuple of valid arguments for the supplied function.
        """
        return inspect.getfullargspec(func).args

    def accepts_kwargs(func: Callable) -> bool:
        """
        Returns True if the function accepts keyword arguments.
        """
        return inspect.getfullargspec(func).varkw is not None

    if accepts_kwargs(func):
        return args_dict

    valid_args = get_valid_args(func)

    return {k: v for k, v in args_dict.items() if k in valid_args}


def safe_call(func, dict_args: dict | None, **kwargs) -> Any:
    """
    Safely calls the supplied function with the supplied dictionary of arguments.
    by removing any invalid arguments.
    """

    if dict_args is None:
        dict_args = {}

    if kwargs:
        dict_args.update(kwargs)

    try:
        return func(**get_valid_call(func, dict_args))
    except TypeError:
        return func(**dict_args)
