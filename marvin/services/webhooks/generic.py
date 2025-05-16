from marvin.repos import AllRepositories

from .base_webhook import BaseWebhook
from sqlalchemy.orm.session import Session


class GenericWebhook(BaseWebhook):
    """
    `GenericWebhook` class is the data access layer for all actions within
    marvin. Database uses composition from classes derived from AccessModel. These
    can be substantiated from the AccessModel class or through inheritance when
    additional methods are required.
    """

    def info(self) -> str:
        return f"Blalalalal Webhook {self._group_id}"
