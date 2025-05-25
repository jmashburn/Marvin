"""
This module handles the configuration of logging for the Marvin application.

It allows loading logging configurations from JSON files, supporting different
configurations for production, development, and testing environments. It also
supports substituting placeholders in the configuration files.
"""
import json
import logging
import pathlib
import typing
from logging import config as logging_config

__dir = pathlib.Path(__file__).parent
__conf: dict[str, str] | None = None


def _log_config(path: pathlib.Path, subsitutions: dict[str, str] | None = None) -> dict[str, typing.Any]:
    """
    Loads a logging configuration from a JSON file.

    Args:
        path (pathlib.Path): The path to the JSON configuration file.
        subsitutions (dict[str, str] | None, optional): A dictionary of substitutions
            to apply to the configuration file. Defaults to None.

    Returns:
        dict[str, typing.Any]: The loaded logging configuration.
    """
    with open(path) as file:
        if subsitutions:
            contents = file.read()
            for key, value in subsitutions.items():
                contents = contents.replace(f"${{{key}}}", value)

            json_data = json.loads(contents)

        else:
            json_data = json.load(file)
    return json_data


def log_config() -> dict[str, str]:
    """
    Returns the current logging configuration.

    Raises:
        ValueError: If the logger has not been configured yet.

    Returns:
        dict[str, str]: The current logging configuration.
    """
    if __conf is None:
        raise ValueError("Logger not configured, must call configured_logger_first")
    return __conf


def configured_logger(
    *,
    mode: str,
    config_override: pathlib.Path | None = None,
    substitutions: dict[str, str] | None = None,
) -> logging.Logger:
    """
    Configured the logger based on the mode and return the root logger

    Args:
        mode (str): The mode to configure the logger for production,dev or testings
        config_override (pathlib.Path), optional): A path to custom logging config. Defaults to None.
        substitutions (dict[str, str], optional): A dictionary of substitutions to apply to the logging config
    """

    global __conf

    if config_override:
        __conf = _log_config(config_override, substitutions)
    else:
        if mode == "production":
            __conf = _log_config(__dir / "logconf.prod.json", substitutions)
        elif mode == "development":
            __conf = _log_config(__dir / "logconf.dev.json", substitutions)
        elif mode == "testing":
            __conf = _log_config(__dir / "logconf.test.json", substitutions)
        else:
            raise ValueError(f"Invalid mode: {mode}")

    logging_config.dictConfig(config=__conf)
    return logging.getLogger()
