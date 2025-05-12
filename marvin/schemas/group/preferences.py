from pydantic import UUID4, ConfigDict
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.db.models.groups import Groups
from marvin.db.models.groups.preferences import GroupPreferencesModel
from marvin.schemas._marvin import _MarvinModel


class GroupPreferencesModel(_MarvinModel): ...


class GroupPreferencesUpdate(GroupPreferencesModel):
    group_id: UUID4
    private_group: bool = True
    first_day_of_week: int = 0


class GroupPreferencesCreate(GroupPreferencesUpdate): ...


class GroupPreferencesRead(GroupPreferencesUpdate):
    id: UUID4
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [
            joinedload(GroupPreferencesModel).load_only(Groups.group_id),
        ]
