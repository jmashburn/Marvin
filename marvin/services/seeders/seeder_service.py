from marvin.repos.repository_factory import AllRepositories

# $from marvin.repos.seeders
from marvin.services import BaseService
from marvin.repos.seed.seeders import NotifierOptionSeeder


class SeederService(BaseService):
    def __init__(self, repos: AllRepositories) -> None:
        super().__init__()
        self.repos = repos

    def seed_notifier_options(self, name: str | None = None) -> None:
        seeder = NotifierOptionSeeder(self.repos, self.logger)
        seeder.seed(name)
