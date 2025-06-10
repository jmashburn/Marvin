"""
This module defines the SQLAlchemy model for group invitation tokens.

It includes the `GroupInviteToken` model, which stores tokens that can be used
to invite users to a specific group. Each token can have a limited number of uses.
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, orm
from sqlalchemy.orm import Mapped, Session, mapped_column  # Added Session for __init__

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .groups import Groups


class GroupInviteToken(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing an invitation token for a group.

    Invite tokens are used to allow users to join a specific group.
    They can be configured with a certain number of allowed uses.
    """

    __tablename__ = "invite_tokens"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the invite token.")
    token: Mapped[str] = mapped_column(String, index=True, nullable=False, unique=True, doc="The unique token string itself.")
    uses_left: Mapped[int] = mapped_column(Integer, nullable=False, default=1, doc="Number of times this token can still be used.")

    # Foreign key to the Groups model
    group_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("groups.id"), index=True, doc="ID of the group this invite token belongs to.")
    # Relationship to the parent Group
    group: Mapped[Optional["Groups"]] = orm.relationship("Groups", back_populates="invite_tokens")

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """
        Initializes a GroupInviteToken instance.

        Attributes are set by the `auto_init` decorator from `kwargs`.
        The `session` argument is required by `auto_init`.

        Args:
            session (Session): The SQLAlchemy session, required by `auto_init`.
            **kwargs: Attributes for the model, such as `token`, `uses_left`,
                      and `group_id` or `group`.
        """
        # All initialization is handled by auto_init based on kwargs.
        # Example:
        # new_token = GroupInviteToken(session=db_session, token="randomstring", uses_left=5, group_id=group.id)
        pass
