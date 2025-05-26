"""
This module defines the SQLAlchemy model for group-specific preferences.

It includes the `GroupPreferencesModel`, which stores various settings and
preferences that can be configured for each user group.
"""

from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Mapped, Session, mapped_column  # Added Session for __init__

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .groups import Groups


class GroupPreferencesModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing preferences for a user group.

    This model stores settings like whether a group is private and what the
    first day of the week should be for display purposes within that group.
    """

    __tablename__ = "group_preferences"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the group preferences entry.")

    # Foreign key to the Groups model, establishing a one-to-one relationship
    # as each group has one set of preferences.
    group_id: Mapped[GUID] = mapped_column(
        GUID,
        sa.ForeignKey("groups.id"),
        nullable=False,
        index=True,
        unique=True,
        doc="ID of the group these preferences belong to.",
    )
    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="preferences")

    # Preference settings
    private_group: Mapped[bool | None] = mapped_column(
        sa.Boolean, default=True, doc="If True, the group is private and not publicly visible. Defaults to True."
    )
    first_day_of_week: Mapped[int | None] = mapped_column(
        sa.Integer,
        default=0,
        doc="The first day of the week (e.g., 0 for Sunday, 1 for Monday). Defaults to 0 (Sunday).",
    )
    # Add other group-specific preference fields here as needed.

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """
        Initializes a GroupPreferencesModel instance.

        Attributes are set by the `auto_init` decorator from `kwargs`.
        The `session` argument is required by `auto_init`.

        Args:
            session (Session): The SQLAlchemy session, required by `auto_init`.
            **kwargs: Attributes for the model, such as `private_group`,
                      `first_day_of_week`, and `group_id` or `group`.
        """
        # All initialization is handled by auto_init based on kwargs.
        # Example:
        # prefs = GroupPreferencesModel(session=db_session, private_group=False, first_day_of_week=1, group_id=group.id)
        pass
