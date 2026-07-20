"""Resources repository."""

from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform import ResourceTags, Resources
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import ResourceRead


class ResourcesRepository(GroupRepositoryGeneric):
    """Repository for managing resources."""

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Resources,
            schema=ResourceRead,
            group_id=group_id,
        )

    def create(self, data: Any) -> ResourceRead:
        data_dict = data if isinstance(data, dict) else data.model_dump()
        tag_ids = data_dict.pop("tag_ids", None)
        resource = super().create(data_dict)
        if tag_ids:
            self._replace_tags(resource.id, tag_ids)
            resource = self.get_one(resource.id)
        return resource

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> ResourceRead:
        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)
        tag_ids = data_dict.pop("tag_ids", None)
        resource = super().update(match_value, data_dict, match_key=match_key)
        if tag_ids is not None:
            self._replace_tags(resource.id, tag_ids)
            resource = self.get_one(resource.id)
        return resource

    def _replace_tags(self, resource_id: UUID4, tag_ids: list[UUID4]) -> None:
        """Replace all tags on a resource (empty list clears them)."""
        self.session.query(ResourceTags).filter(ResourceTags.resource_id == resource_id).delete()
        seen: set = set()
        for tag_id in tag_ids or []:
            if tag_id in seen:
                continue
            seen.add(tag_id)
            self.session.add(ResourceTags(resource_id=resource_id, tag_id=tag_id))
        self.session.commit()
