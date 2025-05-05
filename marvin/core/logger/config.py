import json
import logging
import pathlib
import typing
from logging import config as logging_config

__dir = pathlib.Path(__file__).parent
__conf: dict[str, str] | None = None


def _log_config(path: pathlib.Path, subsitutions: dict[str, str] | None = None) -> dict[str, typing.Any]:
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
