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
    from ..groups import Groups # For relationship typing
    from marvin.db.models.events.events import EventNotifierOptionsModel as GlobalEventNotifierOptionsModel


class GroupEventNotifierOptionsModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a specific notification option for a group's event notifier.

    This table links a `GroupEventNotifierModel` to the specific system-wide
    notification events (identified by namespace and slug) that are active for it.
    """

    __tablename__ = "group_events_notifier_options"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for this group-specific notifier option entry.")
    namespace: Mapped[str] = mapped_column(String, nullable=False, doc="Namespace of the global event notifier option (e.g., 'email', 'webhook').")
    slug: Mapped[str] = mapped_column(String, nullable=False, doc="Slug of the global event notifier option (e.g., 'new_user_signup').")
    # Note: There isn't a unique constraint on (namespace, slug, group_event_notifiers_id) here,
    # which might be intended or an oversight depending on desired behavior.

    # Foreign key to the GroupEventNotifierModel this option belongs to
    group_event_notifiers_id: Mapped[GUID | None] = mapped_column(
        GUID, ForeignKey("group_events_notifiers.id"), index=True, doc="ID of the parent GroupEventNotifierModel."
    )
    # Relationship back to the parent GroupEventNotifierModel
    group_event_notifiers: Mapped["GroupEventNotifierModel"] = orm.relationship(
        "GroupEventNotifierModel", back_populates="options"
    )

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
    apprise_url: Mapped[str] = mapped_column(String, nullable=False, doc="The Apprise URL for sending notifications (e.g., 'slack://tokenA/tokenB/tokenC').")

    # Foreign key to the Groups model
    group_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("groups.id"), index=True, doc="ID of the group this notifier belongs to.")
    # Relationship to the parent Group
    group: Mapped[Optional["Groups"]] = orm.relationship(
        "Groups", back_populates="group_event_notifiers", single_parent=True # single_parent implies cascading deletes if group is deleted
    )

    # Relationship to the specific notification options enabled for this notifier
    options: Mapped[list["GroupEventNotifierOptionsModel"]] = orm.relationship(
        "GroupEventNotifierOptionsModel", back_populates="group_event_notifiers", cascade="all, delete-orphan"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True, # Keep this if model uses non-standard types not shown
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

        # Initialize self.options as an empty list before populating
        self.options = []

        # 1. Populate with globally enabled system notifications by default
        globally_enabled_options: list[GlobalEventNotifierOptionsModel] = (
            session.execute(select(GlobalEventNotifierOptionsModel).filter(GlobalEventNotifierOptionsModel.enabled == True))
            .scalars()
            .all()
        )
        if globally_enabled_options:
            for global_opt in globally_enabled_options:
                # Create a GroupEventNotifierOptionsModel instance for each global option
                # This assumes that by default, a new group notifier subscribes to all globally active events.
                # The `enabled` flag on GroupEventNotifierOptionsModel itself isn't present in the model,
                # so its existence in this list implies it's "on" for this notifier.
                # If `GroupEventNotifierOptionsModel` had an `enabled` flag, it would be set here.
                group_opt_instance = GroupEventNotifierOptionsModel(
                    session=session, # Pass session for its own auto_init if needed
                    namespace=global_opt.namespace,
                    slug=global_opt.slug,
                    # group_event_notifiers_id would be set by relationship append if not handled by auto_init for child
                )
                self.options.append(group_opt_instance)

        # 2. If specific `options` are provided by the user, adjust `self.options`.
        # This part seems to intend to ADD specific options if they aren't already effectively enabled
        # or perhaps ensure ONLY these are enabled. The current logic appends.
        # A more robust approach might be to:
        #   a) If `options` is not None, clear default options and only add specified ones.
        #   OR
        #   b) If `options` is not None, ensure these are present and enabled, potentially disabling others
        #      if `GroupEventNotifierOptionsModel` had its own `enabled` field.
        # Current logic: appends, potentially leading to duplicates if a global option is also in `options`.
        # This needs careful review based on intended behavior.
        # For now, documenting the current append behavior.
        if options is not None:
            # It might be better to build a set of existing (namespace, slug) pairs in self.options
            # to avoid adding duplicates.
            existing_option_keys = {(opt.namespace, opt.slug) for opt in self.options}

            for option_str in options:
                try:
                    namespace, slug = option_str.split(".", 1)
                except ValueError:
                    # Handle cases where option_str is not in "namespace.slug" format
                    # Or log a warning/error
                    # For now, assume valid format or let it raise implicitly later if split fails.
                    # Adding explicit error handling for robustness:
                    raise ValueError(f"Invalid option format: '{option_str}'. Expected 'namespace.slug'.")


                # Check if this specific option is already added from global defaults
                if (namespace, slug) not in existing_option_keys:
                    # Fetch the global option to ensure it's valid
                    global_option_to_add: GlobalEventNotifierOptionsModel | None = (
                        session.execute(
                            select(GlobalEventNotifierOptionsModel).filter_by(namespace=namespace, slug=slug)
                        )
                        .scalars()
                        .one_or_none() # Use one_or_none for safety
                    )

                    if global_option_to_add is None:
                        # This means a requested option string (e.g., "email.non_existent_event")
                        # does not correspond to any defined system notification.
                        raise ValueError(
                            f"Notification option '{option_str}' does not exist in system-wide EventNotifierOptionsModel."
                        )

                    # Add this specific option to the notifier's list
                    specific_group_opt = GroupEventNotifierOptionsModel(
                        session=session,
                        namespace=global_option_to_add.namespace,
                        slug=global_option_to_add.slug,
                    )
                    self.options.append(specific_group_opt)
                    existing_option_keys.add((namespace, slug)) # Add to set to track
        # `auto_init` will handle other kwargs passed to this __init__
