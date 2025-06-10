"""
This module defines Pydantic schemas related to reports generated within or for
user groups in the Marvin application.

It includes enumerations for report categories and statuses, as well as schemas
for creating and representing report entries and the reports themselves. These
are used for API interactions involving group-specific reporting functionalities.
"""

import datetime
import enum  # For creating enumerations

from pydantic import UUID4, ConfigDict, Field  # Core Pydantic components

# SQLAlchemy ORM imports for loader_options method
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

# Marvin specific imports
from marvin.db.models._model_utils.datetime import get_utc_now  # Default timestamp factory
from marvin.db.models.groups import ReportModel as ReportSQLModel  # SQLAlchemy model, aliased
from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model


class ReportCategory(str, enum.Enum):
    """
    Enumeration for the categories of reports that can be generated.
    """

    backup = "backup"  # Report related to data backup operations.
    restore = "restore"  # Report related to data restore operations.
    migration = "migration"  # Report related to data or schema migrations.
    bulk_import = "bulk_import"  # Report related to bulk data import operations.
    # Add other categories as needed, e.g., "system_check", "user_activity"


class ReportSummaryStatus(str, enum.Enum):
    """
    Enumeration for the possible statuses of a report summary.
    """

    in_progress = "in-progress"  # The report generation is currently in progress.
    success = "success"  # The report generation completed successfully.
    failure = "failure"  # The report generation failed.
    partial = "partial"  # The report generation completed with partial success or some errors.


class ReportEntryCreate(_MarvinModel):
    """
    Schema for creating a new entry within a report.
    Each entry details a specific step or item in the report process.
    """

    report_id: UUID4
    """The unique identifier of the parent report this entry belongs to."""
    timestamp: datetime.datetime = Field(default_factory=get_utc_now)
    """Timestamp of when this entry was created (UTC). Defaults to the current UTC time."""
    success: bool = True
    """Indicates if the operation related to this entry was successful. Defaults to True."""
    message: str
    """A descriptive message for this report entry (e.g., "User data backed up", "File X imported")."""
    exception: str = ""
    """Details of any exception that occurred, if applicable. Defaults to an empty string."""


class ReportEntryRead(ReportEntryCreate):
    """
    Schema for representing a report entry when read from the system.
    Extends `ReportEntryCreate` by adding the unique `id` of the entry.
    """

    id: UUID4
    """The unique identifier of the report entry."""
    # Inherits report_id, timestamp, success, message, exception
    model_config = ConfigDict(from_attributes=True)  # Allows creating from ORM model attributes


class ReportCreateModel(_MarvinModel):
    """
    Base model for report creation, currently a placeholder.

    NOTE: This model is defined as a placeholder (`...`). It might be intended
    for future common fields shared by different report creation schemas, or it
    could be an artifact. `ReportCreate` directly inherits from this.
    """

    ...  # Ellipsis indicates a placeholder, no fields defined here.


class ReportCreate(ReportCreateModel):
    """
    Schema for creating a new report.
    """

    timestamp: datetime.datetime = Field(default_factory=get_utc_now)
    """Timestamp of when this report was initiated (UTC). Defaults to the current UTC time."""
    category: ReportCategory
    """The category of the report (e.g., backup, migration)."""
    group_id: UUID4
    """The unique identifier of the group this report is associated with."""
    name: str
    """A user-defined name for the report (e.g., "Monthly Backup - January", "User Data Import")."""
    status: ReportSummaryStatus = ReportSummaryStatus.in_progress
    """The initial status of the report. Defaults to "in-progress"."""


class ReportSummary(ReportCreate):
    """
    Schema for a summary representation of a report.
    Extends `ReportCreate` by adding the unique `id` of the report.
    This might be used in listings where full entry details are not needed.
    """

    id: UUID4
    """The unique identifier of the report."""
    # Inherits timestamp, category, group_id, name, status


class ReportRead(ReportSummary):
    """
    Schema for representing a full report when read from the system, including its entries.
    Extends `ReportSummary`.
    """

    entries: list[ReportEntryRead] = []
    """A list of entries associated with this report. Defaults to an empty list."""

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        """
        Provides SQLAlchemy loader options for optimizing queries for `ReportRead`.

        Configures eager loading for the `entries` relationship using `joinedload`.
        This helps prevent N+1 query problems when fetching a report along with all
        its associated entries.

        Returns:
            list[LoaderOption]: A list of SQLAlchemy loader options.
        """
        # Eagerly load the 'entries' relationship when querying for ReportSQLModel
        return [joinedload(ReportSQLModel.entries)]
