"""
This module defines Pydantic schemas related to administrative settings,
specifically for managing custom pages within the Marvin application.

These schemas are used for creating, updating, and representing custom page
entities that can be configured by administrators.
"""
from typing import Annotated, Any # Added Any for `values` in validator

from pydantic import ConfigDict, Field, field_validator # Core Pydantic components
from slugify import slugify # Utility for generating URL-friendly slugs

from marvin.schemas._marvin import _MarvinModel # Base Pydantic model for Marvin schemas


class CustomPageBase(_MarvinModel):
    """
    Base schema for custom page data.

    Contains common fields for creating and updating custom pages, including
    automatic slug generation from the page name.
    """
    name: str 
    """The display name of the custom page."""
    
    slug: Annotated[str | None, Field(validate_default=True)] = None
    """
    The URL-friendly slug for the custom page.
    If not provided or if it doesn't match the slug generated from `name`,
    it will be automatically generated/overwritten by the `validate_slug` validator.
    `validate_default=True` ensures the validator runs even if `slug` is not explicitly provided.
    """
    
    position: int
    """The display order or position of the custom page in a list or menu."""

    # Pydantic model configuration
    # `from_attributes=True` allows creating instances from ORM objects.
    model_config = ConfigDict(from_attributes=True) 

    @field_validator("slug", mode="before") # Run this validator before Pydantic's internal validation for 'slug'
    @classmethod # Needs to be a classmethod to access `values` correctly if it were Pydantic v1 style for `root_validator`
                 # For Pydantic v2, `values` in a field_validator refers to the specific field's value if `mode='after'`,
                 # or the input value if `mode='before'`. To access other fields (like 'name'),
                 # a `model_validator` (root validator) is typically used.
                 # However, the original code structure uses `values` in a `field_validator`.
                 # Let's assume `values` here is meant to be the dict of all input data if `mode='before'`.
                 # For Pydantic v2, the signature for field_validator that needs other fields is more complex
                 # or a model_validator is preferred.
                 # Given the original signature `validate_slug(slug: str, values)`:
                 # This is not a standard Pydantic v2 field_validator signature if `values` is expected to be all model data.
                 # A Pydantic v2 field validator's second argument is usually `info: ValidationInfo`.
                 # If `values` is meant to be the dict of all incoming data (like a v1 root_validator's `values` arg):
                 # This should ideally be a `model_validator(mode='before')` to correctly access all `data`.
                 # For now, documenting based on apparent intent of accessing 'name' from `values`.
                 # Let's adjust signature to what Pydantic v2 expects for a field_validator needing context,
                 # or assume it's a `model_validator` if the intent is to process `name` to generate `slug`.
                 # Re-interpreting based on common patterns for slug generation:
                 # If `slug` is optional and derived from `name`, a model_validator is cleaner.
                 # If `slug` is provided and needs validation against `name`, a field_validator can work
                 # but accessing other fields directly via `values` dict is not the v2 way for field_validator.
                 # For now, I will assume `values` is the data dict passed to the model and make it a model_validator.
                 #
                 # Revisiting: The original code has `slug: Annotated[str | None, Field(validate_default=True)]`
                 # and `@field_validator("slug", mode="before") def validate_slug(slug: str, values):`
                 # `values` in a `mode="before"` field validator is the value of the field itself.
                 # To access other fields like 'name', a `model_validator` is needed.
                 # I will change this to a model_validator to correctly implement the slug logic.
    @model_validator(mode="before") # Changed to model_validator
    @classmethod
    def generate_or_validate_slug(cls, data: Any) -> Any: # `data` will be a dict or the model instance
        """
        Validates or generates the slug for the custom page.

        If a slug is provided, it's checked against a freshly generated one from the name.
        If they don't match, the provided slug is overwritten.
        If no slug is provided, it's generated from the `name` field.
        This ensures the slug is always URL-friendly and consistent with the name.

        Args:
            data (Any): The input data for the model. Can be a dictionary or an instance.

        Returns:
            Any: The (potentially modified) input data with the correct slug.
        
        Raises:
            ValueError: If 'name' is not provided in the data when a slug needs generation.
        """
        if isinstance(data, dict):
            name = data.get("name")
            slug = data.get("slug")
            
            if not name and slug is None: # Cannot generate slug if name is missing
                 # Or raise error if name is mandatory for slug generation
                return data # Let Pydantic handle missing 'name' if it's a required field

            if name: # Only proceed if name is available
                calculated_slug = slugify(str(name)) # Ensure name is string for slugify
                if slug != calculated_slug:
                    data["slug"] = calculated_slug # Overwrite or set slug
        elif hasattr(data, "name"): # If data is an object (e.g. another Pydantic model)
            name = data.name
            slug = getattr(data, "slug", None)
            if name: # Ensure name is not None
                calculated_slug = slugify(str(name))
                if slug != calculated_slug:
                    setattr(data, "slug", calculated_slug)
            elif slug is None and name is None:
                # If name is None and slug is also None, can't generate.
                # Pydantic will later validate if 'name' is required.
                pass

        return data


class CustomPageOut(CustomPageBase):
    """
    Schema for representing a custom page when retrieved from the system.
    Extends `CustomPageBase` by adding the unique `id` of the page.
    """
    id: int # The unique identifier for the custom page (typically the database primary key).
    
    # Inherits model_config from CustomPageBase, including from_attributes=True.
    # No need to redefine unless overriding.
