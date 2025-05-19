from pydantic import UUID4

from marvin.core.config import get_app_settings
from marvin.repos.all_repositories import get_repositories
from marvin.repos.repository_factory import AllRepositories
from marvin.schemas.group import GroupCreate
from marvin.schemas.group.preferences import GroupPreferencesCreate
from marvin.services import BaseService


class GroupService(BaseService):
    def __init__(self, group_id: UUID4, repos: AllRepositories):
        self.group_id = group_id
        self.repos = repos
        super().__init__()

    @staticmethod
    def create_group(repos: AllRepositories, group: GroupCreate, prefs: GroupPreferencesCreate | None = None):
        """
        Creates a new group in the database with the required associated table references to ensure
        the group includes required preferences.
        """
        new_group = repos.groups.create(group)

        if prefs is None:
            prefs = GroupPreferencesCreate(group_id=new_group.id)
        else:
            prefs.group_id = new_group.id

        group_repos = get_repositories(repos.session, group_id=new_group.id)
        group_preferences = group_repos.group_preferences.create(prefs)

        settings = get_app_settings()

        new_group.preferences = group_preferences

        return new_group
