"""Assets repository."""

from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform import AssetTags, Assets
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import AssetRead


class AssetsRepository(GroupRepositoryGeneric):
    """Repository for managing assets."""

    def __init__(self, session: Session, group_id: UUID4 | None) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Assets,
            schema=AssetRead,
            group_id=group_id,
        )

    def update(self, match_value: Any, new_data: Any, match_key: str | None = None) -> AssetRead:
        # Assets are created via upload; tags are applied here (PATCH) or via the attach endpoint.
        data_dict = new_data if isinstance(new_data, dict) else new_data.model_dump(exclude_unset=True)
        tag_ids = data_dict.pop("tag_ids", None)
        asset = super().update(match_value, data_dict, match_key=match_key)
        if tag_ids is not None:
            self._replace_tags(asset.id, tag_ids)
            asset = self.get_one(asset.id)
        return asset

    def _replace_tags(self, asset_id: UUID4, tag_ids: list[UUID4]) -> None:
        """Replace all tags on an asset (empty list clears them)."""
        self.session.query(AssetTags).filter(AssetTags.asset_id == asset_id).delete()
        seen: set = set()
        for tag_id in tag_ids or []:
            if tag_id in seen:
                continue
            seen.add(tag_id)
            self.session.add(AssetTags(asset_id=asset_id, tag_id=tag_id))
        self.session.commit()
