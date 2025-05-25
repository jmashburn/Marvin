"""
This module defines SQLAlchemy models for generating and managing reports
within user groups.

It includes:
- `ReportEntryModel`: Represents a single entry or line item within a report.
- `ReportModel`: Represents a report, which can contain multiple entries and
  is associated with a specific group.
"""
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import ConfigDict
from sqlalchemy import Boolean, ForeignKey, String, orm
from sqlalchemy.orm import Mapped, Session, mapped_column # Added Session for __init__

from marvin.db.models import BaseMixins, SqlAlchemyBase
from .._model_utils.auto_init import auto_init
from .._model_utils.datetime import NaiveDateTime, get_utc_now
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from .groups import Groups


class ReportEntryModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a single entry within a report.

    Each entry can indicate success/failure, include a message, an exception (if any),
    and is timestamped.
    """

    __tablename__ = "report_entries"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the report entry.")

    success: Mapped[bool | None] = mapped_column(Boolean, default=False, doc="Indicates if the operation related to this entry was successful.")
    message: Mapped[str | None] = mapped_column(String, nullable=True, doc="A descriptive message for this report entry.") # Corrected Mapped[str] to Mapped[str | None]
    exception: Mapped[str | None] = mapped_column(String, nullable=True, doc="Details of any exception that occurred, if applicable.") # Corrected Mapped[str] to Mapped[str | None]
    timestamp: Mapped[datetime] = mapped_column(NaiveDateTime, nullable=False, default=get_utc_now, doc="Timestamp of when this entry was created (UTC).")

    # Foreign key to the ReportModel this entry belongs to
    report_id: Mapped[GUID] = mapped_column(GUID, ForeignKey("group_reports.id"), nullable=False, index=True, doc="ID of the parent report.")
    # Relationship to the parent ReportModel
    report: Mapped["ReportModel"] = orm.relationship("ReportModel", back_populates="entries")

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """
        Initializes a ReportEntryModel instance.

        Attributes are set by the `auto_init` decorator from `kwargs`.
        The `session` argument is required by `auto_init`.

        Args:
            session (Session): The SQLAlchemy session, required by `auto_init`.
            **kwargs: Attributes for the model.
        """
        pass


class ReportModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a report associated with a group.

    A report has a name, status, category, timestamp, and can contain multiple
    report entries.
    """

    __tablename__ = "group_reports"

    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the report.")

    name: Mapped[str] = mapped_column(String, nullable=False, doc="Name of the report.")
    status: Mapped[str] = mapped_column(String, nullable=False, doc="Current status of the report (e.g., 'running', 'completed', 'failed').")
    category: Mapped[str] = mapped_column(String, index=True, nullable=False, doc="Category of the report (e.g., 'system_check', 'data_export').")
    timestamp: Mapped[datetime] = mapped_column(NaiveDateTime, nullable=False, default=get_utc_now, doc="Timestamp of when this report was created or last updated (UTC).")

    # Relationship to ReportEntryModel (one-to-many: one report has many entries)
    entries: Mapped[list["ReportEntryModel"]] = orm.relationship(
        "ReportEntryModel", back_populates="report", cascade="all, delete-orphan", doc="List of entries within this report."
    )

    # Foreign key to the Groups model
    group_id: Mapped[GUID] = mapped_column(GUID, ForeignKey("groups.id"), nullable=False, index=True, doc="ID of the group this report belongs to.")
    # Relationship to the parent Group
    group: Mapped["Groups"] = orm.relationship("Groups", back_populates="group_reports", single_parent=True)

    model_config = ConfigDict(
        arbitrary_types_allowed=True, # Standard Pydantic config
        # Exclude 'entries' from default Pydantic serialization to prevent large data transfers
        # or circular dependencies if entries are also serialized with back-references.
        exclude={"entries"}
    )

    @auto_init()
    def __init__(self, session: Session, **kwargs) -> None:
        """
        Initializes a ReportModel instance.

        Attributes are set by the `auto_init` decorator from `kwargs`.
        The `session` argument is required by `auto_init`.

        Args:
            session (Session): The SQLAlchemy session, required by `auto_init`.
            **kwargs: Attributes for the model.
        """
        pass
