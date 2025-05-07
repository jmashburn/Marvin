from marvin.core import root_logger

logger = root_logger.get_logger()


def ping():
    logger.debug("Ping")
