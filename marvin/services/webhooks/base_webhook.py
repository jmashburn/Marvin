from pydantic import UUID4
from sqlalchemy.orm import Session

from ...repos._utils import NOT_SET, NotSet


class BaseWebhook:
    """
    BaseWebhook class is the data access layer for all actions within
    marvin. Database uses composition from classes derived from AccessModel. These
    can be substantiated from the AccessModel class or through inheritance when
    additional methods are required.
    """

    session: Session

    _group_id: UUID4 | None = None

    def __init__(self, session: Session, group_id: UUID4 | None = None) -> None:
        self.session = session
        self._group_id = group_id

    @property
    def group_id(self) -> UUID4 | None:
        return self._group_id

    def info(self) -> str:
        """
        Info a new webhook
        """
        raise NotImplementedError("This method should be implemented in subclasses")

    def create(self, **kwargs) -> None:
        """
        Create a new webhook
        """
        raise NotImplementedError("This method should be implemented in subclasses")

    def update(self, **kwargs) -> None:
        """
        Update an existing webhook
        """
        raise NotImplementedError("This method should be implemented in subclasses")

    def delete(self, **kwargs) -> None:
        """
        Delete an existing webhook
        """
        raise NotImplementedError("This method should be implemented in subclasses")
