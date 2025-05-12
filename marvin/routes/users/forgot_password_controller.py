from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm.session import Session

from marvin.db.db_setup import generate_session
from marvin.schemas.user.password import ForgotPassword, ResetPassword
from marvin.services.user.password_reset_service import PasswordResetService

router = APIRouter(prefix="")


@router.post("/forgot-password")
def forgot_password(
    email: ForgotPassword,
    session: Session = Depends(generate_session),
    accept_language: Annotated[str | None, Header()] = None,
):
    """Sends an email with a reset link to the user"""
    f_service = PasswordResetService(session)
    return f_service.send_reset_email(email.email, accept_language)


@router.post("/reset-password")
def reset_password(reset_password: ResetPassword, session: Session = Depends(generate_session)):
    """Resets the user password"""
    f_service = PasswordResetService(session)
    return f_service.reset_password(reset_password.token, reset_password.password)
