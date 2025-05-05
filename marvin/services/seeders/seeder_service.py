from marvin.repos.repository_factory import AllRepositories

# $from marvin.repos.seeders
from marvin.services import BaseService


class SeederService(BaseService):
    def __init__(self, repos: AllRepositories) -> None:
        super().__init__()
        self.repos = repos
