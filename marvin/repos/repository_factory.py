from collections.abc import Sequence
from functools import cached_property

from sqlalchemy import select
from sqlalchemy.orm import Session


# class RepositoryCategories(RepositoryGeneric[CategoryOut, Category]):
#     def get_empty(self) -> Sequence[Category]:
#         stmt = select(Category).filter


class AllRepositories:
    def __init__(self, session: Session) -> None:
        """
        `AllRepositories` class is the data access layer for all database actions.
        Database uses composition from classes derived from AccessModel. These
        can be substantiated from the AccessModel class or through inheritance when
        additional methods are required.
        """
        self.session = session
