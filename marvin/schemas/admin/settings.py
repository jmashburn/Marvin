from typing import Annotated

from pydantic import ConfigDict, Field, field_validator
from slugify import slugify

from marvin.schemas._marvin import _MarvinModel


class CustomPageBase(_MarvinModel):
    name: str
    slug: Annotated[str | None, Field(validate_default=True)]
    position: int
    model_config = ConfigDict(from_attributes=True)

    @field_validator("slug", mode="before")
    def validate_slug(slug: str, values):
        name: str = values["name"]
        calc_slug: str = slugify(name)

        if slug != calc_slug:
            slug = calc_slug

        return slug


class CustomPageOut(CustomPageBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
