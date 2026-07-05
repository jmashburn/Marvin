"""Assets repository."""

from typing import Any

from pydantic import UUID4
from sqlalchemy.orm import Session

from marvin.db.models.platform import Assets
from marvin.repos.repository_generic import GroupRepositoryGeneric
from marvin.schemas.platform import AssetCreate, AssetRead


class AssetsRepository(GroupRepositoryGeneric):
    """Repository for managing assets."""

    def __init__(self, session: Session, group_id: UUID4) -> None:
        super().__init__(
            session=session,
            primary_key="id",
            sql_model=Assets,
            schema=AssetRead,
        )
        self._group_id = group_id

    @staticmethod
    def _map_metadata(data: Any, *, exclude_unset: bool = False) -> Any:
        """Map public asset metadata to the SQLAlchemy-safe attribute name."""
        data_dict = data.copy() if isinstance(data, dict) else data.model_dump(exclude_unset=exclude_unset)
        if "metadata" in data_dict:
            data_dict["metadata_"] = data_dict.pop("metadata")
        return data_dict

    def create(self, data: AssetCreate | dict) -> AssetRead:
        return super().create(self._map_metadata(data))

    def update(self, match_value: Any, new_data: AssetCreate | dict, match_key: str | None = None) -> AssetRead:
        return super().update(match_value, self._map_metadata(new_data, exclude_unset=True), match_key)
