from pydantic import UUID4, ConfigDict
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from marvin.schemas._marvin import _MarvinModel

from ...db.models.users import PasswordResetModel, Users
from .user import PrivateUser


class ForgotPassword(_MarvinModel):
    email: str


class PasswordResetToken(_MarvinModel):
    token: str


class ValidateResetToken(_MarvinModel):
    token: str


class ResetPassword(ValidateResetToken):
    email: str
    password: str
    passwordConfirm: str


class SavePasswordResetToken(_MarvinModel):
    user_id: UUID4
    token: str


class PrivatePasswordResetToken(SavePasswordResetToken):
    user: PrivateUser
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        return [
            selectinload(PasswordResetModel.user).joinedload(Users.group),
            selectinload(PasswordResetModel.user).joinedload(Users.tokens),
        ]
