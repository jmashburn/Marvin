"""
This module defines the SQLAlchemy model for user groups.

It includes the `Groups` model, which represents a user group within the application.
Groups can have associated users, preferences, invite tokens, webhooks, reports,
and event notifiers.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from pydantic import ConfigDict
from sqlalchemy.orm import Mapped, Session, mapped_column  # Added Session for __init__ type hint

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

# preferences is directly imported and used, ensure it's available
from .preferences import GroupPreferencesModel

if TYPE_CHECKING:
    from ..users import Users
    from .events import GroupEventNotifierModel
    from .invite_tokens import GroupInviteToken
    from .reports import ReportModel
    from .webhooks import GroupWebhooksModel


class Groups(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a user group.

    A group acts as a container for users and various group-specific settings
    and associated entities.
    """

    __tablename__ = "groups"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the group.")
    name: Mapped[str] = mapped_column(sa.String, index=True, nullable=False, unique=True, doc="Human-readable name of the group, must be unique.")
    slug: Mapped[str | None] = mapped_column(sa.String, index=True, unique=True, doc="URL-friendly slug for the group, must be unique if set.")

    # Relationship to Users model (one-to-many: one group has many users)
    users: Mapped[list["Users"]] = orm.relationship("Users", back_populates="group")

    # Relationship to GroupPreferencesModel (one-to-one: one group has one preferences object)
    preferences: Mapped["GroupPreferencesModel"] = orm.relationship(
        "GroupPreferencesModel",  # Corrected typing to use defined import
        back_populates="group",
        uselist=False,  # Indicates a one-to-one relationship
        single_parent=True,  # Group is the parent, deletion cascades
        cascade="all, delete-orphan",  # Operations on Group cascade to preferences
        doc="Group-specific preferences.",
    )

    # Common arguments for several one-to-many relationships from Group
    # These relationships imply that the related objects are owned by the group
    # and should be deleted if the group is deleted.
    _common_relationship_args = {
        "back_populates": "group",  # Sets up bidirectional relationship
        "cascade": "all, delete-orphan",  # Cascades operations (especially delete)
        "single_parent": True,  # Ensures the related object has only one parent group
    }

    # Relationship to GroupInviteToken (one-to-many)
    invite_tokens: Mapped[list["GroupInviteToken"]] = orm.relationship(
        "GroupInviteToken", **_common_relationship_args, doc="Invite tokens associated with this group."
    )
    # Relationship to GroupWebhooksModel (one-to-many)
    webhooks: Mapped[list["GroupWebhooksModel"]] = orm.relationship(
        "GroupWebhooksModel", **_common_relationship_args, doc="Webhooks configured for this group."
    )
    # Relationship to ReportModel (one-to-many)
    group_reports: Mapped[list["ReportModel"]] = orm.relationship(
        "ReportModel", **_common_relationship_args, doc="Reports generated for or by this group."
    )
    # Relationship to GroupEventNotifierModel (one-to-many)
    group_event_notifiers: Mapped[list["GroupEventNotifierModel"]] = orm.relationship(
        "GroupEventNotifierModel", **_common_relationship_args, doc="Event notifiers configured for this group."
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Standard Pydantic config
        # Fields to exclude from Pydantic model serialization by default.
        # This is useful if these fields are large, sensitive, or cause circular dependencies
        # when converting the SQLAlchemy model to a Pydantic model.
        exclude={
            "users",
            "webhooks",
            "preferences",
            "invite_tokens",
            # "group_reports" and "group_event_notifiers" might also be candidates for exclusion
            # depending on serialization needs.
        },
    )

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """
        Initializes a Groups instance.

        Attributes are set by the `auto_init` decorator from `kwargs`.
        The `session` argument is required by `auto_init` if any relationships
        need to be processed that involve database lookups or creations.

        Args:
            session (Session): The SQLAlchemy session, required by `auto_init`.
            **kwargs: Attributes for the model, processed by `auto_init`.
                      This can include 'name', 'slug', and data for related objects
                      like 'preferences' if structured according to `auto_init`'s expectations.
        """
        # All initialization is handled by auto_init based on kwargs.
        # For example, to create a group with preferences:
        # group = Groups(session=db_session, name="My Group", slug="my-group", preferences={"setting_a": True})
        pass
