"""
This module provides utility functions for mapping and casting data between
Pydantic model instances.

These functions are helpful for transforming data from one schema representation
to another, for example, when converting an API request model to a database model,
or a database model to an API response model.
"""
from typing import TypeVar, Any # Added Any for **kwargs

from pydantic import BaseModel # Base Pydantic model for type hinting

# Define TypeVars for generic type hinting, ensuring inputs are Pydantic models.
T = TypeVar("T", bound=BaseModel) # Represents the destination model type.
U = TypeVar("U", bound=BaseModel) # Represents the source model type.


def mapper(source: U, dest: T, **_: Any) -> T: # Added Any type for unused kwargs placeholder
    """
    Maps attribute values from a `source` Pydantic model instance to a `dest`
    Pydantic model instance.

    This function iterates through the fields of the `source` model. If a field
    with the same name exists in the `dest` model, its value in `dest` is updated
    with the value from `source`. The `dest` model instance is modified in-place
    and also returned. Only top-level fields are mapped.

    The `**_` parameter indicates that any additional keyword arguments passed to
    this function will be ignored.

    Args:
        source (U): The source Pydantic model instance from which values are read.
        dest (T): The destination Pydantic model instance to which values are written.
                  This object is modified directly.
        **_ (Any): Catches any additional keyword arguments, which are ignored.

    Returns:
        T: The modified `dest` Pydantic model instance with updated values.
    """
    # Iterate over all fields defined in the source model
    for field_name in source.model_fields:
        # Check if the destination model also has a field with the same name
        if field_name in dest.model_fields:
            # If so, set the attribute on the destination model with the value from the source model
            setattr(dest, field_name, getattr(source, field_name))
    
    return dest # Return the modified destination model


def cast(source: U, target_cls: type[T], **kwargs: Any) -> T: # Renamed dest to target_cls for clarity
    """
    Casts a `source` Pydantic model instance to a new instance of `target_cls` type.

    This function creates a new instance of `target_cls`. It copies values for fields
    that exist in both the `source` model and `target_cls`. Additionally, any
    keyword arguments (`**kwargs`) provided will be passed to the `target_cls`
    constructor, potentially overriding values copied from the `source` or providing
    values for fields not present in the `source`.

    This is useful for transforming data between different Pydantic schema types,
    especially when creating a new object based on an existing one with some modifications
    or additions.

    Args:
        source (U): The source Pydantic model instance.
        target_cls (type[T]): The Pydantic model class to cast the source into.
        **kwargs (Any): Additional keyword arguments to initialize the `target_cls` instance.
                        These can override values from `source` or provide new ones.

    Returns:
        T: A new instance of `target_cls` populated with data from `source` and `kwargs`.
    """
    # Extract data from the source model for fields that are also present in the target class
    create_data = {
        field_name: getattr(source, field_name)
        for field_name in source.model_fields # Iterate fields of the source model
        if field_name in target_cls.model_fields # Check if field also exists in the target class
    }
    # Update this dictionary with any additional keyword arguments provided.
    # Kwargs will override values if there are common keys.
    create_data.update(kwargs or {})
    
    # Create and return a new instance of the target class using the combined data
    return target_cls(**create_data)
