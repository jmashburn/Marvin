from typing import Annotated

from pydantic import Field, StringConstraints, field_validator
from pydantic_core.core_schema import ValidationInfo

from marvin.schemas._marvin import _MarvinModel


class UserRegistrationCreate(_MarvinModel):
    group: str | None = None
    group_token: Annotated[str | None, Field(validate_default=True)] = None
    email: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)]
    username: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)]
    full_name: Annotated[str, StringConstraints(strip_whitespace=True)]
    password: str
    password_confirm: str
    advanced: bool = False
    private: bool = False

    seed_data: bool = False

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, value, info: ValidationInfo):
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("passwords do not match")
        return value

    @field_validator("group_token")
    @classmethod
    def group_or_token(cls, value, info: ValidationInfo):
        if not bool(value) and not bool(info.data["group"]):
            raise ValueError("group or group_token must be provided")

        return value
