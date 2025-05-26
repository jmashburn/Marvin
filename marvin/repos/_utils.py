"""
This module provides utility objects, primarily for handling optional parameters
where `None` might be a valid value, and a different sentinel is needed to
indicate that a parameter was not set at all.
"""


class NotSet:
    """
    A sentinel class used to represent a value that has not been set.

    This is useful in situations where `None` is a valid value for a parameter,
    and a different indicator is needed to signify that the parameter was not
    provided by the caller.

    Instances of `NotSet` evaluate to `False` in a boolean context.
    """

    def __bool__(self) -> bool:
        """
        Makes instances of NotSet evaluate to False in boolean contexts.
        """
        return False


NOT_SET = NotSet()
"""
A global instance of the `NotSet` class, to be used as a default value or
placeholder for parameters that have not been explicitly set.
"""
