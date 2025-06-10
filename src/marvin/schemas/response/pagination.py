"""
This module defines Pydantic schemas and enumerations for handling pagination,
ordering, and filtering in API requests and responses within the Marvin application.

It provides:
- Enums for order direction (`OrderDirection`) and null positioning (`OrderByNullPosition`).
- Base models for request query parameters (`RequestQuery`) and pagination-specific
  query parameters (`PaginationQuery`).
- A generic base model for paginated API responses (`PaginationBase`), which includes
  methods for generating 'next' and 'previous' page links.
"""

import enum  # For creating enumerations
from typing import Annotated, Any, Generic, TypeVar  # Standard typing utilities
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit  # For URL manipulation

from humps import camelize  # For converting snake_case to camelCase (used in set_pagination_guides)
from pydantic import BaseModel, Field, field_validator  # Core Pydantic components

# from pydantic import UUID4 # UUID4 was imported but not used
from pydantic_core.core_schema import ValidationInfo  # For accessing validation context

from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model for Marvin schemas

# Generic TypeVar for the data items in a paginated response.
# Ensures that `items` will be a list of Pydantic models.
DataT = TypeVar("DataT", bound=BaseModel)


class OrderDirection(str, enum.Enum):
    """
    Enumeration for specifying the direction of ordering in queries.
    """

    asc = "asc"  # Ascending order.
    desc = "desc"  # Descending order.


class OrderByNullPosition(str, enum.Enum):
    """
    Enumeration for specifying how NULL values should be positioned in ordered results.
    """

    first = "first"  # Position NULL values at the beginning.
    last = "last"  # Position NULL values at the end.


class RequestQuery(_MarvinModel):
    """
    Base schema for common request query parameters related to ordering and filtering.
    """

    order_by: str | None = None
    """Field name to order results by. Can be comma-separated for multiple fields."""
    order_by_null_position: OrderByNullPosition | None = None
    """Specifies how to position NULL values if ordering by a nullable field. (e.g., 'first', 'last')."""
    order_direction: OrderDirection = OrderDirection.desc
    """Direction of ordering ('asc' or 'desc'). Defaults to 'desc'."""
    query_filter: str | None = None
    """A string representing advanced query filters (e.g., using a specific filter syntax)."""
    pagination_seed: Annotated[str | None, Field(validate_default=True)] = None
    """
    A seed for random pagination if `order_by` is set to "random".
    Required when `order_by` is "random" to ensure stable pagination across requests.
    `validate_default=True` ensures the validator runs even if the field is not provided.
    """

    @field_validator("pagination_seed", mode="before")
    @classmethod
    def validate_pagination_seed_if_random_order(
        cls, pagination_seed_value: str | None, info: ValidationInfo
    ) -> str | None:  # Renamed v to pagination_seed_value
        """
        Validates that `pagination_seed` is provided if `order_by` is "random".

        Args:
            pagination_seed_value (str | None): The value of the `pagination_seed` field.
            info (ValidationInfo): Pydantic validation context, providing access to other field values.

        Returns:
            str | None: The validated `pagination_seed_value`.

        Raises:
            ValueError: If `order_by` is "random" and `pagination_seed` is not provided.
        """
        # Access other field values from info.data (which holds the input data for the model)
        if info.data and info.data.get("order_by") == "random" and not pagination_seed_value:
            raise ValueError("`pagination_seed` is required when `order_by` is 'random'.")
        return pagination_seed_value


class PaginationQuery(RequestQuery):
    """
    Schema for pagination-specific query parameters, extending `RequestQuery`.
    Includes parameters for page number and items per page.
    """

    page: int = Field(default=1, ge=1)
    """The page number to retrieve (1-indexed). Defaults to 1. Must be >= 1."""
    per_page: int = Field(default=50, ge=-1)  # Allow -1 for "all items"
    """
    Number of items to retrieve per page. Defaults to 50.
    A value of -1 typically means "all items" (no pagination limit). Must be >= -1.
    """


class PaginationBase(BaseModel, Generic[DataT]):
    """
    A generic base schema for paginated API responses.

    It includes pagination metadata such as current page, items per page, total items,
    total pages, and links for 'next' and 'previous' pages. The actual list of
    items is typed by the generic `DataT`.

    Type Parameters:
        DataT: The Pydantic model type for the items in the `items` list.
    """

    page: int = 1
    """Current page number (1-indexed)."""
    per_page: int = 10
    """Number of items per page."""
    total: int = 0
    """Total number of items across all pages."""
    total_pages: int = 0
    """Total number of pages."""
    items: list[DataT]
    """List of items for the current page, typed by `DataT`."""
    next: str | None = None
    """URL for the next page of results, if available; otherwise None."""
    previous: str | None = None
    """URL for the previous page of results, if available; otherwise None."""

    def _set_next(self, base_route_path: str, current_query_params: dict[str, Any]) -> None:
        """
        Sets the 'next' page URL if applicable.

        If the current page is not the last page, it constructs the URL for the next page
        by incrementing the 'page' parameter in `current_query_params`.

        Args:
            base_route_path (str): The base path of the current endpoint (e.g., from `request.url.path`).
            current_query_params (dict[str, Any]): A dictionary of the current request's query parameters.
                                                This dictionary will be modified.
        """
        if self.page >= self.total_pages:  # No next page if current is last or beyond
            self.next = None
            return

        # Update query parameters for the next page
        current_query_params["page"] = self.page + 1
        # Generate the full URL for the next page
        self.next = PaginationBase.merge_query_parameters(base_route_path, current_query_params)

    def _set_prev(self, base_route_path: str, current_query_params: dict[str, Any]) -> None:
        """
        Sets the 'previous' page URL if applicable.

        If the current page is not the first page, it constructs the URL for the previous page
        by decrementing the 'page' parameter in `current_query_params`.

        Args:
            base_route_path (str): The base path of the current endpoint.
            current_query_params (dict[str, Any]): A dictionary of the current request's query parameters.
                                                This dictionary will be modified.
        """
        if self.page <= 1:  # No previous page if current is first or less
            self.previous = None
            return

        # Update query parameters for the previous page
        current_query_params["page"] = self.page - 1
        # Generate the full URL for the previous page
        self.previous = PaginationBase.merge_query_parameters(base_route_path, current_query_params)

    def set_pagination_guides(self, base_route_path: str, original_query_params: dict[str, Any] | None) -> None:
        """
        Populates the 'next' and 'previous' pagination guide URLs.

        It first sanitizes the current `self.page` value. Then, it prepares a dictionary
        of query parameters (camelCasing them if `original_query_params` are provided)
        and calls `_set_next` and `_set_prev` to generate the navigation links.

        Args:
            base_route_path (str): The base path of the endpoint (e.g., from `request.url.path`
                                   or `router.url_path_for("...")`).
            original_query_params (dict[str, Any] | None): The original query parameters from the
                                                           request, used to construct links.
                                                           These are camelCased.
        """
        # Ensure query parameters are in camelCase for URL generation, as APIs often use camelCase.
        # Create a mutable copy for modification.
        processed_query_params: dict[str, Any] = camelize(original_query_params) if original_query_params else {}

        # Sanitize current page number (ensure it's at least 1)
        self.page = max(self.page, 1)

        # Set next and previous page URLs
        # Pass a copy of processed_query_params to _set_next and _set_prev to avoid unintended shared modifications
        # if they modify the dict directly for different link generations.
        self._set_next(base_route_path, processed_query_params.copy())
        self._set_prev(base_route_path, processed_query_params.copy())

    @staticmethod
    def merge_query_parameters(url_path: str, params_to_merge: dict[str, Any]) -> str:
        """
        Constructs a URL string by merging new or updated query parameters with an existing URL path.

        If the `url_path` already contains query parameters, they are preserved, and
        `params_to_merge` will update or add to them.

        Args:
            url_path (str): The base URL or path string. Can include existing query parameters.
            params_to_merge (dict[str, Any]): A dictionary of query parameters to add or update.
                                           Keys are parameter names, values are parameter values.
                                           List values are supported for multiple parameters with the same name.

        Returns:
            str: The new URL string with merged query parameters.
        """
        # Split the URL into its components
        scheme, netloc, path, query_string, fragment = urlsplit(url_path)

        # Parse existing query parameters from the URL
        existing_query_params = parse_qs(query_string)
        existing_query_params.update(params_to_merge)

        # Rebuild the query string
        new_query_string = urlencode(existing_query_params, doseq=True)

        # Reconstruct the full URL
        return urlunsplit((scheme, netloc, path, new_query_string, fragment))
