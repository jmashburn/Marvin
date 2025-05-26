"""
This module defines the SQLAlchemy model for event notifier options.

It includes the `EventNotifierOptionsModel` which stores configuration
for different types of event notifications within the application.
"""

from typing import TYPE_CHECKING

from pydantic import ConfigDict  # Imported though not explicitly used, implies Pydantic integration
from slugify import slugify
from sqlalchemy import Boolean, String, orm
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    # from ..groups import Groups # This import is commented out, implies no current direct FK to Groups
    pass


class EventNotifierOptionsModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing options for event notifiers.

    Each instance defines a specific notification that can be enabled or disabled,
    belonging to a namespace and having a human-readable name and a slug.
    """

    __tablename__ = "events_notifier_options"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the event notifier option.")
    namespace: Mapped[str] = mapped_column(String, nullable=False, doc="Namespace for grouping related notifier options (e.g., 'email', 'webhook').")
    name: Mapped[str] = mapped_column(String, nullable=False, doc="Human-readable name for the notifier option (e.g., 'New User Signup').")
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, doc="URL-friendly slug, automatically generated from the name.")
    description: Mapped[str | None] = mapped_column(String, nullable=True, doc="Optional description of what this notifier option does.")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, doc="Indicates if this notification option is currently active.")

    # Pydantic model_config, if used for serialization/validation by the application
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @hybrid_property
    def option(self) -> str:
        """
        Returns a fully qualified option string, combining namespace and slug.

        Example: "email.new_user_signup"
        """
        return self.namespace + "." + self.slug

    @auto_init()
    def __init__(self, session: orm.Session, name: str, **kwargs) -> None:
        """
        Initializes an EventNotifierOptionsModel instance.

        The `slug` is automatically generated from the `name` upon initialization.
        Other attributes are handled by the `auto_init` decorator.

        Args:
            session (orm.Session): The SQLAlchemy session, required by `auto_init`.
            name (str): The human-readable name for the notifier option. This will be
                        used to generate the slug.
            **kwargs: Additional keyword arguments for other model attributes,
                      processed by `auto_init`.
        """
        # The `auto_init` decorator will handle assigning kwargs to attributes.
        # We explicitly set the slug here based on the provided name.
        # Ensure `name` is passed via kwargs if not explicitly handled before `auto_init`.
        # However, `auto_init` typically processes all kwargs. If `name` is in kwargs,
        # it would be set. The explicit `name` arg here is for slugification.
        # If `name` is also a mapped_column and in kwargs, `auto_init` will set it.
        # This __init__ primarily exists for the slug generation logic.
        if name:  # Ensure name is provided for slugification
            self.slug = slugify(name)
        # The `auto_init` decorator will then process all items in `kwargs`,
        # including `name` if it's passed in `kwargs` and is a model attribute.
        # If `name` is only passed as an explicit arg to __init__ and not in kwargs,
        # and `name` is a Mapped column, it should also be in kwargs for auto_init to see it.
        # Current setup: `name` is a Mapped column. `auto_init` will handle it if `name` is in `kwargs`.
        # The `name` parameter in `__init__` signature is used here for `slugify`.
        # It's assumed `name` will also be in `kwargs` if it needs to be set on the model field by `auto_init`.
        # If `auto_init` runs before this, `self.name` would be set. If after, this `name` param is used.
        # Given `auto_init` wraps this, this code runs first.
        # So, `name` kwarg will be processed by `auto_init` after this.
        # Consider if `name` kwarg should be removed by `auto_init` if handled here.
        # For safety, ensure `name` passed to `slugify` is the intended one.
        # The `**_` in the original signature was changed to `**kwargs` for clarity.
        # `auto_init` will call the original init (this one) and then set attributes.
        # This means `self.slug` is set, then `auto_init` sets other fields from kwargs.
        # If `name` is in `kwargs`, `auto_init` will set `self.name`.
