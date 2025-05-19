import datetime
import enum

from pydantic import ConfigDict, Field
from pydantic.types import UUID4
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.db.models._model_utils.datetime import get_utc_now
from marvin.db.models.groups import ReportModel
from marvin.schemas._marvin import _MarvinModel


class ReportCategory(str, enum.Enum):
    backup = "backup"
    restore = "restore"
    migration = "migration"
    bulk_import = "bulk_import"


class ReportSummaryStatus(str, enum.Enum):
    in_progress = "in-progress"
    success = "success"
    failure = "failure"
    partial = "partial"


class ReportEntryCreate(_MarvinModel):
    report_id: UUID4
    timestamp: datetime.datetime = Field(default_factory=get_utc_now)
    success: bool = True
    message: str
    exception: str = ""


class ReportEntryRead(ReportEntryCreate):
    id: UUID4
    model_config = ConfigDict(from_attributes=True)


class ReportCreateModel(_MarvinModel): ...


class ReportCreate(ReportCreateModel):
    timestamp: datetime.datetime = Field(default_factory=get_utc_now)
    category: ReportCategory
    group_id: UUID4
    name: str
    status: ReportSummaryStatus = ReportSummaryStatus.in_progress


class ReportSummary(ReportCreate):
    id: UUID4


class ReportRead(ReportSummary):
    entries: list[ReportEntryRead] = []
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [joinedload(ReportModel.entries)]
