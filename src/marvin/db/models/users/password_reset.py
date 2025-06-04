"""
This module defines the SQLAlchemy model for password reset tokens.

It includes the `PasswordResetModel`, which stores tokens generated for users
who request a password reset. These tokens are associated with a user and are
typically short-lived and single-use.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, orm
from sqlalchemy.orm import Mapped, mapped_column

from .. import BaseMixins, SqlAlchemyBase  # Assuming BaseMixins provides id, created_at, updated_at
from .._model_utils.guid import GUID  # For user_id type

if TYPE_CHECKING:
    from .users import Users


class PasswordResetModel(SqlAlchemyBase, BaseMixins):
    """
    SQLAlchemy model representing a password reset token.

    This model links a securely generated token to a user, allowing them to
    reset their password. The `id` column from `BaseMixins` serves as the primary key.
    """

    __tablename__ = "password_reset_tokens"
    # `id` (PK), `created_at`, `updated_at` are inherited from BaseMixins
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate, doc="Unique identifier for the token.")
    # Foreign key to the Users model
    user_id: Mapped[GUID] = mapped_column(
        GUID,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="The ID of the user who requested the password reset.",
    )
    # Relationship to the User who owns this token
    # `uselist=False` indicates a one-to-one relationship from the perspective of this token
    # (one token belongs to one user). A user might have multiple tokens over time,
    # but `password_reset_tokens` on `Users` model would be a list.
    user: Mapped["Users"] = orm.relationship("Users", back_populates="password_reset_tokens")

    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="The securely generated password reset token string. Indexed for quick lookups.",
    )
    # Consider adding an `expires_at: Mapped[datetime]` column for token expiry.
    # Consider adding a `used: Mapped[bool]` column to mark token as used.

    def __init__(self, user_id: GUID, token: str, **_) -> None:
        """
        Initializes a PasswordResetModel instance.

        Args:
            user_id (GUID): The ID of the user this token is for.
            token (str): The generated password reset token.
            **kwargs: Additional keyword arguments, potentially for `BaseMixins`
                      if it has its own __init__ or uses `auto_init`.
                      If `BaseMixins` has `auto_init`, `session` might be needed in `kwargs`.
        """
        self.user_id = user_id
        self.token = token
