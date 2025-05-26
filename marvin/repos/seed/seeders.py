"""
This module provides specific seeder implementations for various data types
within the Marvin application.

Currently, it includes:
- `NotifierOptionSeeder`: For seeding default event notifier options from a JSON file.
"""

import json
import pathlib
from collections.abc import Generator

# from functools import cached_property # This import was not used
from marvin.schemas.event.event import EventNotifierOptionsCreate
from marvin.services.event_bus_service.event_types import EventNameSpace  # Default namespace

from .abstract_seeder import AbstractSeeder  # Base seeder class

# Assuming notifier_options is a module or object that has a `notifier_options` attribute
# which is a Path object pointing to the default JSON file.
from .resources import notifier_options as default_notifier_options_resource


class NotifierOptionSeeder(AbstractSeeder):
    """
    A seeder for populating the database with event notifier options.

    This seeder reads notifier option definitions from a JSON file. It can
    load from a locale-specific file within the SEED_DIR or fall back to a
    default set of notifier options packaged with the application.
    """

    _namespace: str = EventNameSpace.namespace.name  # Default namespace if not specified in JSON

    def get_file(self, name: str) -> pathlib.Path:
        """
        Determines the path to the notifier options JSON file.

        It first checks for a locale-specific file in the configured SEED_DIR
        (e.g., `DATA_DIR/seeds/notifier_options/{name}.json`). If not found,
        it falls back to the default `notifier_options.json` file provided
        in the `marvin.repos.seed.resources.notifier_options` package.

        Args:
            name (str): The name of the seeder configuration (e.g., "notifier_options"),
                        used to construct the path to the locale-specific file.
                        Typically, this would be something like 'notifier_options'.

        Returns:
            pathlib.Path: The path to the JSON file to be loaded.
        """
        # Construct path for user-overrideable, locale-specific seed data
        locale_specific_path = self.directories.SEED_DIR / "notifier_options" / f"{name}.json"

        if locale_specific_path.exists():
            self.logger.info(f"Using locale-specific notifier options file: {locale_specific_path}")
            return locale_specific_path
        else:
            # Fallback to the default packaged resource file
            # Ensure default_notifier_options_resource.notifier_options is a Path object
            default_path = getattr(default_notifier_options_resource, "notifier_options", None)
            if not isinstance(default_path, pathlib.Path) or not default_path.exists():
                raise FileNotFoundError("Default notifier_options.json resource not found or configured incorrectly.")
            self.logger.info(f"Using default notifier options file: {default_path}")
            return default_path

    def load_data(self, name: str) -> Generator[EventNotifierOptionsCreate, None, None]:
        """
        Loads notifier option data from the determined JSON file.

        It parses the JSON file, assigns a default namespace if one is not
        provided in the data, and yields `EventNotifierOptionsCreate` Pydantic
        schemas for each unique notifier option. Duplicate names are skipped.

        Args:
            name (str): The name of the seeder configuration, passed to `get_file`.

        Yields:
            Generator[EventNotifierOptionsCreate, None, None]: A generator of
                Pydantic schemas ready for database insertion.
        """
        json_file_path = self.get_file(name)
        file_content = json_file_path.read_text(encoding="utf-8")
        options_data = json.loads(file_content)

        seen_notifier_option_names = set()  # To track names and avoid duplicates
        for option_dict in options_data:
            option_name = option_dict.get("name")
            if not option_name:
                self.logger.warning(f"Skipping notifier option due to missing 'name': {option_dict}")
                continue

            if option_name in seen_notifier_option_names:
                self.logger.warning(f"Skipping duplicate notifier option name: '{option_name}'")
                continue

            # Assign default namespace if not present in the data
            if "namespace" not in option_dict:
                option_dict["namespace"] = self._namespace

            seen_notifier_option_names.add(option_name)
            try:
                yield EventNotifierOptionsCreate(**option_dict)
            except Exception as e:  # Catch Pydantic validation errors or other issues
                self.logger.error(f"Error validating notifier option data '{option_name}': {e}. Data: {option_dict}")

    def seed(self, name: str | None = None) -> None:
        """
        Seeds the database with notifier options.

        It loads data using `load_data` and attempts to create each notifier
        option in the database via the `event_notifier_options` repository.
        Any errors during creation are logged.

        Args:
            name (str): The name of the seeder configuration, typically
                        "notifier_options", which is passed to `load_data`.
        """
        self.logger.info(f"Seeding Notifier Options from configuration: '{name}'")
        count_seeded = 0
        count_errors = 0
        for notifier_option_schema in self.load_data(name):
            try:
                self.repos.event_notifier_options.create(notifier_option_schema)
                self.logger.debug(
                    f"Successfully seeded notifier option: {notifier_option_schema.namespace}.{notifier_option_schema.slug or notifier_option_schema.name}"
                )
                count_seeded += 1
            except Exception as e:  # Catch database errors or other issues
                self.logger.error(f"Failed to seed notifier option '{notifier_option_schema.name}': {e}")
                count_errors += 1
        self.logger.info(f"Notifier options seeding complete. Seeded: {count_seeded}, Errors: {count_errors}")
