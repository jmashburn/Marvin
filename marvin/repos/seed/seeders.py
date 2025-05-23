import json
import pathlib
from collections.abc import Generator
from functools import cached_property
from marvin.schemas.event.event import EventNotifierOptionsCreate
from marvin.services.event_bus_service.event_types import EventNameSpace
from .abstract_seeder import AbstractSeeder
from .resources import notifier_options


class NotifierOptionSeeder(AbstractSeeder):
    _namespace = EventNameSpace.namespace

    def get_file(self, name: str) -> pathlib.Path:
        locale_path = self.directories.SEED_DIR / "notifier_options" / f"{name}.json"
        return locale_path if locale_path.exists() else notifier_options.notifier_options

    def load_data(self, name: str) -> Generator[EventNotifierOptionsCreate, None, None]:
        file = self.get_file(name)

        seen_notifier_options = set()
        for notifier_option in json.loads(file.read_text(encoding="utf-8")):
            if notifier_option["name"] in seen_notifier_options:
                continue

            if "namespace" not in notifier_option:
                notifier_option["namespace"] = self._namespace
            seen_notifier_options.add(notifier_option["name"])
            yield EventNotifierOptionsCreate(**notifier_option)

    def seed(self, name: str) -> None:
        self.logger.info("Seeding Notifier Options")
        for notifier_option in self.load_data(name):
            try:
                self.repos.event_notifier_options.create(notifier_option)
            except Exception as e:
                self.logger.error(e)
