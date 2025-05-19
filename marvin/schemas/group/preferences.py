from pydantic import UUID4, ConfigDict
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.db.models.groups import Groups
from marvin.db.models.groups.preferences import GroupPreferencesModel
from marvin.schemas._marvin import _MarvinModel


class GroupPreferencesCreate(_MarvinModel):
    group_id: UUID4
    model_config = ConfigDict(from_attributes=True)


class GroupPreferencesRead(GroupPreferencesCreate):
    id: UUID4
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [
            joinedload(GroupPreferencesModel).load_only(Groups.group_id),
        ]


class GroupPreferencesUpdate(GroupPreferencesRead):
    private_group: bool = True
    first_day_of_week: int = 0
    model_config = ConfigDict(from_attributes=True)
