"""
This module defines SQLAlchemy models related to group-specific event notifications.

It includes:
- `GroupEventNotifierOptionsModel`: Represents specific notification options
  enabled or configured for a `GroupEventNotifier`.
- `GroupEventNotifierModel`: Represents a notification service (e.g., an Apprise URL)
  configured for a group, along with its specific notification event preferences.
"""

from typing import TYPE_CHECKING, Optional

from pydantic import ConfigDict
from sqlalchemy import Boolean, ForeignKey, String, orm, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, Session, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from ..groups import Groups  # For relationship typing


class GroupEventNotifierOptionsModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a specific notification option for a group's event notifier.

    This table links a `GroupEventNotifierModel` to the specific system-wide
    notification events (identified by namespace and slug) that are active for it.
    """

    __tablename__ = "group_events_notifier_options"

    id: Mapped[GUID] = mapped_column(
        GUID,
        primary_key=True,
        default=GUID.generate,
        doc="Unique identifier for this group-specific notifier option entry.",
    )
    namespace: Mapped[str] = mapped_column(String, nullable=False, doc="Namespace of the global event notifier option (e.g., 'email', 'webhook').")
    slug: Mapped[str] = mapped_column(String, nullable=False, doc="Slug of the global event notifier option (e.g., 'new_user_signup').")
    # Note: There isn't a unique constraint on (namespace, slug, group_event_notifiers_id) here,
    # which might be intended or an oversight depending on desired behavior.

    # Foreign key to the GroupEventNotifierModel this option belongs to
    group_event_notifiers_id: Mapped[GUID | None] = mapped_column(
        GUID, ForeignKey("group_events_notifiers.id"), index=True, doc="ID of the parent GroupEventNotifierModel."
    )
    # Relationship back to the parent GroupEventNotifierModel
    group_event_notifiers: Mapped["GroupEventNotifierModel"] = orm.relationship("GroupEventNotifierModel", back_populates="options")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @hybrid_property
    def option(self) -> str:
        """
        Returns the fully qualified option string (namespace.slug).
        """
        return self.namespace + "." + self.slug

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """
        Initializes a GroupEventNotifierOptionsModel instance.

        Attributes are set by the `auto_init` decorator from `kwargs`.
        The `session` argument is required by `auto_init`.

        Args:
            session (Session): The SQLAlchemy session.
            **kwargs: Attributes for the model, processed by `auto_init`.
        """
        # All initialization is handled by auto_init based on kwargs
        pass


class GroupEventNotifierModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model for a group's event notifier configuration.

    This defines a specific notification channel (e.g., an Apprise URL) for a group
    and links to the set of notification events (`GroupEventNotifierOptionsModel`)
    that are active for this channel.
    """

    __tablename__ = "group_events_notifiers"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the group event notifier.")
    name: Mapped[str] = mapped_column(String, nullable=False, doc="User-defined name for this notifier (e.g., 'Admin Slack Channel').")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="Whether this notifier configuration is currently active.")
    apprise_url: Mapped[str] = mapped_column(
        String, nullable=False, doc="The Apprise URL for sending notifications (e.g., 'slack://tokenA/tokenB/tokenC')."
    )

    # Foreign key to the Groups model
    group_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("groups.id"), index=True, doc="ID of the group this notifier belongs to.")
    # Relationship to the parent Group
    group: Mapped[Optional["Groups"]] = orm.relationship(
        "Groups",
        back_populates="group_event_notifiers",
        single_parent=True,  # single_parent implies cascading deletes if group is deleted
    )

    # Relationship to the specific notification options enabled for this notifier
    options: Mapped[list["GroupEventNotifierOptionsModel"]] = orm.relationship(
        "GroupEventNotifierOptionsModel", back_populates="group_event_notifiers", cascade="all, delete-orphan"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Keep this if model uses non-standard types not shown
        # Pydantic config to exclude 'options' during serialization if needed,
        # especially if 'options' are handled separately or could cause circular issues.
        exclude={"options"},
    )

    @auto_init()
    def __init__(self, session: Session, options: list[str] | None = None, **kwargs) -> None:
        """
        Initializes a GroupEventNotifierModel instance.

        Sets up the notifier and its associated event options.
        - Default options are populated based on globally enabled `EventNotifierOptionsModel`.
        - If `options` (a list of "namespace.slug" strings) are provided, these specific
          options are enabled for this notifier, overriding defaults for those particular events.

        Args:
            session (Session): The SQLAlchemy session, required by `auto_init` and for DB queries.
            options (list[str] | None, optional): A list of "namespace.slug" strings
                representing specific notification events to enable for this notifier.
                Defaults to None, which means all globally enabled system notifications
                will be active for this notifier by default.
            **kwargs: Additional keyword arguments for other model attributes,
                      processed by `auto_init`.
        """
        # Import here to avoid circular dependencies at the module level
        from marvin.db.models.events.events import EventNotifierOptionsModel as GlobalEventNotifierOptionsModel

        self.options = []

        if options is None:
            # No explicit list — subscribe to all globally enabled events by default
            globally_enabled = (
                session.execute(
                    select(GlobalEventNotifierOptionsModel).filter(GlobalEventNotifierOptionsModel.enabled == True)  # noqa: E712
                )
                .scalars()
                .all()
            )
            for global_opt in globally_enabled:
                self.options.append(
                    GroupEventNotifierOptionsModel(session=session, namespace=global_opt.namespace, slug=global_opt.slug)
                )
        else:
            # Explicit list provided — use exactly those (empty list = no subscriptions)
            for option_str in options:
                try:
                    namespace, slug = option_str.split(".", 1)
                except ValueError:
                    raise ValueError(f"Invalid option format: '{option_str}'. Expected 'namespace.slug'.") from None

                global_opt = (
                    session.execute(select(GlobalEventNotifierOptionsModel).filter_by(namespace=namespace, slug=slug))
                    .scalars()
                    .one_or_none()
                )
                if global_opt is None:
                    raise ValueError(f"Notification option '{option_str}' does not exist.") from None

                self.options.append(
                    GroupEventNotifierOptionsModel(session=session, namespace=namespace, slug=slug)
                )
