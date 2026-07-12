"""Entry type repository."""

from typing import Any

from fastapi import HTTPException, status
from pydantic import UUID4, ValidationError
from sqlalchemy.orm import Session

from marvin.core.root_logger import get_logger
from marvin.db.models.platform import Entries, EntryTypes
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import EntryTypeRead
from marvin.schemas.platform.entry_type_rendering import CapabilitiesDefinition, KNOWN_CORE_RENDERERS, RenderingDefinition
from marvin.schemas.platform.entry_type_schema import EntryTypeSchemaDefinition

logger = get_logger(__name__)


class EntryTypesRepository(GroupRepositoryGeneric[EntryTypeRead, EntryTypes]):
    """Repository for workspace-scoped and system-level entry types.

    Validates schema_json against EntryTypeSchemaDefinition when creating/updating.

    System entry types (group_id=NULL, is_system=True) are globally available
    to all workspaces and cannot be modified or deleted via standard methods.
    """

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=EntryTypes,
            schema=EntryTypeRead,
            group_id=group_id,
        )

    def _filter_builder(self, **kwargs):
        """
        Override to include system entry types (group_id IS NULL) in addition
        to workspace-scoped types.

        Returns an empty dict when group_id is set, because we'll handle
        filtering in page_all and other query methods manually.
        """
        # Don't apply automatic group_id filter - we handle it manually
        # to include both workspace types AND system types
        return {}

    def _apply_group_filter(self, query):
        """
        Apply custom group_id filter to include both workspace and system types.

        Args:
            query: SQLAlchemy query to filter

        Returns:
            Filtered query
        """
        from sqlalchemy import or_

        if self.group_id:
            return query.filter(
                or_(
                    self.model.group_id == self.group_id,
                    self.model.group_id.is_(None),
                )
            )
        else:
            # If no group_id, only show system types
            return query.filter(self.model.group_id.is_(None))

    def page_all(self, pagination, override_schema=None, search=None):
        """Override to add custom group_id filtering for system types."""
        # Get the base query from parent
        eff_schema = override_schema or self.schema
        pagination_params = pagination.model_copy(deep=True)

        base_query = self._query(override_schema=eff_schema, with_options=False)

        # Apply custom group_id filter: workspace types OR system types
        base_query = self._apply_group_filter(base_query)

        # Apply text search if provided
        if search:
            base_query = self.add_search_to_query(base_query, eff_schema, search)

        # Default ordering
        if not pagination_params.order_by and not search:
            pagination_params.order_by = "sort_order"

        # Apply pagination
        paginated_query, total_count, total_pages = self.add_pagination_to_query(base_query, pagination_params)

        # Apply loader options
        if hasattr(eff_schema, "loader_options") and callable(eff_schema.loader_options):
            final_query_with_options = paginated_query.options(*eff_schema.loader_options())
        else:
            final_query_with_options = paginated_query

        # Execute query
        items = list(self.session.scalars(final_query_with_options).unique())

        # Convert to schemas
        from marvin.schemas.response import PaginationBase

        schema_items = [eff_schema.model_validate(item) for item in items]

        return PaginationBase(
            page=pagination_params.page,
            per_page=pagination_params.per_page,
            total=total_count,
            total_pages=total_pages,
            items=schema_items,
        )

    def get_one(self, match_value, match_key=None, override_schema=None):
        """Override to include system types in lookup."""
        eff_schema = override_schema or self.schema
        key = match_key or self.primary_key

        query = self._query(override_schema=eff_schema)
        query = self._apply_group_filter(query)
        query = query.filter(getattr(self.model, key) == match_value)

        item = self.session.scalars(query).unique().one_or_none()
        return eff_schema.model_validate(item) if item else None

    def multi_query(self, query_by, start=0, limit=None, override_schema=None, order_by=None, order_descending=True):
        """Override to include system types in multi query."""
        eff_schema = override_schema or self.schema

        query = self._query(override_schema=eff_schema)
        query = self._apply_group_filter(query)

        # Apply query_by filters
        for key, value in query_by.items():
            query = query.filter(getattr(self.model, key) == value)

        # Apply ordering
        if order_by:
            order_attr = getattr(self.model, order_by)
            query = query.order_by(order_attr.desc() if order_descending else order_attr.asc())

        # Apply pagination
        if start:
            query = query.offset(start)
        if limit:
            query = query.limit(limit)

        items = list(self.session.scalars(query).unique())
        return [eff_schema.model_validate(item) for item in items]

    def _validate_schema_json(self, schema_json: dict | None) -> None:
        if schema_json is None:
            return
        try:
            EntryTypeSchemaDefinition.model_validate(schema_json)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid schema definition: {e}",
            )

    def _validate_rendering_json(self, rendering_json: dict | None) -> None:
        if rendering_json is None:
            return
        try:
            RenderingDefinition.model_validate(rendering_json)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rendering definition: {e}",
            )

    def _validate_capabilities_json(self, capabilities_json: dict | None) -> None:
        if capabilities_json is None:
            return
        try:
            CapabilitiesDefinition.model_validate(capabilities_json)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid capabilities definition: {e}",
            )

    def _check_renderer_warnings(self, data_dict: dict) -> list[str]:
        if not data_dict.get("is_rendered"):
            return []
        rendering_json = data_dict.get("rendering_json")
        if not rendering_json:
            return ["Entry type is marked as rendered but has no rendering configuration"]
        renderer = rendering_json.get("renderer")
        if not renderer:
            return ["Entry type is marked as rendered but has no renderer declared"]
        if renderer not in KNOWN_CORE_RENDERERS:
            return [f"Unknown renderer '{renderer}'. Known core renderers: {', '.join(sorted(KNOWN_CORE_RENDERERS))}"]
        return []

    def create(self, data: Any) -> EntryTypeRead:
        from slugify import slugify

        data_dict = data if isinstance(data, dict) else data.model_dump()

        if self.group_id:
            data_dict["group_id"] = self.group_id

        # Auto-generate slug from name if not provided
        if not data_dict.get("slug") and data_dict.get("name"):
            data_dict["slug"] = slugify(data_dict["name"])

        # Map Pydantic field names to DB column names
        if "content_schema" in data_dict:
            data_dict["schema_json"] = data_dict.pop("content_schema")
        if "rendering" in data_dict:
            data_dict["rendering_json"] = data_dict.pop("rendering")
        if "capabilities" in data_dict:
            data_dict["capabilities_json"] = data_dict.pop("capabilities")

        # Validate JSON fields if provided
        if "schema_json" in data_dict:
            self._validate_schema_json(data_dict["schema_json"])
        if "rendering_json" in data_dict:
            self._validate_rendering_json(data_dict["rendering_json"])
        if "capabilities_json" in data_dict:
            self._validate_capabilities_json(data_dict["capabilities_json"])

        warnings = self._check_renderer_warnings(data_dict)
        result = super().create(data_dict)
        if warnings:
            result.warnings = warnings
        return result

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> EntryTypeRead:
        # Check if this is a system entry type
        entry_type = self.get_one(match_value)
        if entry_type and entry_type.is_system and entry_type.group_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System entry types cannot be modified.",
            )

        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)

        # Don't auto-regenerate slug on update - slugs should remain stable once created
        # to avoid breaking references in entries and external integrations
        data_dict.pop("slug", None)

        # Map Pydantic field names to DB column names
        if "content_schema" in data_dict:
            data_dict["schema_json"] = data_dict.pop("content_schema")
        if "rendering" in data_dict:
            data_dict["rendering_json"] = data_dict.pop("rendering")
        if "capabilities" in data_dict:
            data_dict["capabilities_json"] = data_dict.pop("capabilities")

        # Validate JSON fields if provided
        if "schema_json" in data_dict:
            self._validate_schema_json(data_dict["schema_json"])
        if "rendering_json" in data_dict:
            self._validate_rendering_json(data_dict["rendering_json"])
        if "capabilities_json" in data_dict:
            self._validate_capabilities_json(data_dict["capabilities_json"])

        warnings = self._check_renderer_warnings(data_dict)
        data_dict.pop("slug", None)
        data_dict.pop("group_id", None)
        result = super().update(match_value, data_dict, match_key=match_key)
        if warnings:
            result.warnings = warnings
        return result

    def delete(self, value: Any, match_key: str | None = None) -> EntryTypeRead:
        # Check if this is a system entry type
        entry_type = self.get_one(value)
        if entry_type and entry_type.is_system and entry_type.group_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System entry types cannot be deleted.",
            )

        entry_count = self._count_attribute("entry_type_id", value)
        if entry_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Entry type is in use by entries and cannot be deleted.",
            )
        return super().delete(value, match_key=match_key)

    def _count_attribute(self, attribute_name: str, attr_match: Any | None = None) -> int:
        count_query = self.session.query(Entries).filter(getattr(Entries, attribute_name) == attr_match)
        if self.group_id:
            count_query = count_query.filter(Entries.group_id == self.group_id)
        return count_query.count()
