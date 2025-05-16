import datetime
import enum

from isodate import parse_time
from pydantic import UUID4, HttpUrl, ConfigDict, field_validator

from marvin.schemas._marvin import _MarvinModel
from marvin.schemas._marvin.datetime_parser import parse_datetime
from marvin.schemas.response.pagination import PaginationBase
from marvin.services.event_bus_service.event_types import EventDocumentType


class WebhookMethod(str, enum.Enum):
    GET = "GET"
    POST = "POST"
    # PUT = "PUT"
    # DELETE = "DELETE"


class WebhookCreate(_MarvinModel):
    enabled: bool = True
    name: str
    url: HttpUrl
    method: WebhookMethod = WebhookMethod.POST
    webhook_type: EventDocumentType = EventDocumentType.generic
    scheduled_time: datetime.time

    @field_validator("scheduled_time", mode="before")
    @classmethod
    def validate_scheduled_time(cls, v):
        """
        Validator accepts both datetime and time values from external sources.
        DateTime types are parsed and converted to time objects without timezones

        type: time is treated as a UTC value
        type: datetime is treated as a value with a timezone
        """
        parser_funcs = [
            lambda x: parse_datetime(x).astimezone(datetime.timezone.utc).time(),
            parse_time,
        ]

        if isinstance(v, datetime.time):
            return v

        for parser_func in parser_funcs:
            try:
                return parser_func(v)
            except ValueError:
                continue

        raise ValueError(f"Invalid scheduled time: {v}")


class WebhookUpdate(WebhookCreate):
    group_id: UUID4


class WebhookRead(WebhookUpdate):
    id: UUID4
    model_config = ConfigDict(from_attributes=True)


class WebhookPagination(PaginationBase):
    items: list[WebhookRead]
