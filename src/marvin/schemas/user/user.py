"""
This module defines Pydantic schemas related to user entities and their
authentication tokens within the Marvin application.

It includes schemas for:
- Creating, reading, and managing long-lived API tokens.
- User creation, reading (various views like summary, private), and updates.
- Password change operations.
- Paginated responses for user lists.
"""

from datetime import UTC, datetime, timedelta  # Standard datetime utilities
from pathlib import Path  # For path operations (e.g., user directory)
from typing import Annotated, Any, TypeVar  # Standard typing utilities

from pydantic import (  # Core Pydantic components
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,  # Added for validator context
    field_validator,
)

# SQLAlchemy ORM imports for loader_options method
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.interfaces import LoaderOption

# Marvin core and database model imports
from marvin.core.config import get_app_settings
from marvin.db.models.users import Users as UsersSQLModel  # SQLAlchemy User model, aliased
from marvin.db.models.users.users import (
    AuthMethod,
)  # AuthMethod enum and Token model
from marvin.db.models.users.users import (
    LongLiveToken as LongLiveTokenSQLModel,
)
from marvin.schemas._marvin import _MarvinModel  # Base Pydantic model for Marvin schemas
from marvin.schemas.response.pagination import PaginationBase  # Base for pagination responses

# Generic TypeVar, though not actively used in this file's public exports.
DataT = TypeVar("DataT", bound=BaseModel)
# Global application settings instance
settings = get_app_settings()


class LongLiveTokenCreate(_MarvinModel):
    """
    Schema for creating a new long-lived API token (Personal Access Token).
    """

    name: str
    """A user-defined name for the token to help identify its purpose (e.g., "GitHub Actions Token")."""
    integration_id: str = settings._DEFAULT_INTEGRATION_ID
    """
    An optional identifier for an external integration this token might be used with.
    Defaults to "generic".
    """


class LongLiveTokenRead(_MarvinModel):
    """
    Schema for representing a long-lived API token when read from the system.
    This view typically excludes the sensitive token string itself.
    """

    id: UUID4
    """The unique identifier of the API token."""
    user_id: UUID4
    """The unique identifier of the user to whom this token belongs."""
    name: str
    """The user-defined name of the API token."""
    created_at: datetime | None = None  # Should be `datetime` if always present from BaseMixins
    """Timestamp (UTC) of when the token was created."""

    update_at: datetime | None = None  # Should be `datetime` if always present from BaseMixins
    """Timestamp (UTC) of when the token was created."""

    integration_id: str = settings._DEFAULT_INTEGRATION_ID
    """
    An optional identifier for an external integration this token might be used with.
    Defaults to "generic".
    """
    model_config = ConfigDict(from_attributes=True)  # Allows creating from ORM model attributes

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        """
        Provides SQLAlchemy loader options for optimizing queries for `LongLiveTokenRead`.
        Configures eager loading for the `user` relationship of the token.
        """
        # Eagerly load the 'user' related to the LongLiveTokenSQLModel
        return [joinedload(LongLiveTokenSQLModel.user)]


class LongLiveTokenSummary(_MarvinModel):
    id: UUID4
    """The unique identifier of the API token."""
    name: str
    """The user-defined name of the API token."""
    model_config = ConfigDict(from_attributes=True)  # Allows creating from ORM model attributes


class LongLiveTokenCreateResponse(_MarvinModel):  # Extends LongLiveTokenRead to include common fields
    """
    Schema for the response when a new long-lived API token is created.
    Crucially, this schema includes the actual `token` string, which should
    ONLY be returned at the time of creation and not stored or displayed again.
    """

    token: str
    """The generated API token string. This is sensitive and should be handled securely."""
    # Inherits id, name, created_at from LongLiveTokenRead
    model_config = ConfigDict(from_attributes=True)  # Allows creating from ORM model attributes


class LongLiveTokenPagination(PaginationBase):
    """
    Schema for paginated responses containing a list of tokens.
    The items in the list are expected to conform to the `LongLiveTokenSummary` schema.
    """

    items: list[LongLiveTokenSummary]
    """The list of groups for the current page, serialized as `LongLiveTokenSummary`."""


class TokenCreate(LongLiveTokenCreate):  # Extends LongLiveTokenCreate for request data
    """
    Schema used internally for creating a token record in the database.
    Includes the user ID and the hashed token string (if hashing were applied here,
    though JWTs are typically stored as is).
    """

    user_id: UUID4
    """The unique identifier of the user to whom this token belongs."""
    token: str
    """The actual token string to be stored."""
    model_config = ConfigDict(from_attributes=True)


class TokenResponseDelete(_MarvinModel):
    """
    Schema for the response after successfully deleting an API token.
    Confirms which token was deleted by its name.
    """

    token_delete: str  # Field name implies it holds the name of the deleted token.
    """The name of the API token that was successfully deleted."""
    model_config = ConfigDict(from_attributes=True)


class ChangePassword(_MarvinModel):
    """
    Schema for a password change request.
    Requires the user's current password and the new password (min length 8).
    """

    current_password: str = ""  # Default to empty string, but should be required by API.
    """The user's current password, for verification."""
    new_password: str = Field(..., min_length=8)  # `...` denotes a required field.
    """The new password. Must be at least 8 characters long."""


class UserCreate(_MarvinModel):
    """
    Schema for creating a new user.
    Includes essential user details, authentication method, admin status,
    group assignment, permissions, and password.
    """

    id: UUID4 | None = None  # Optional ID, typically auto-generated by the database.
    username: str | None = None
    """Optional username. If not provided, it might default to `full_name` or `email` depending on service logic."""
    full_name: str | None = None
    """The user's full name."""
    email: Annotated[str, StringConstraints(to_lower=True, strip_whitespace=True)]
    """The user's email address. Will be converted to lowercase and stripped of whitespace."""
    auth_method: AuthMethod = AuthMethod.MARVIN
    """The authentication method for the user. Defaults to `MARVIN` (standard password)."""
    admin: bool = False
    """Whether the user has administrative privileges. Defaults to False."""
    group: str | None = None  # Represents group name or ID for assignment. Validator handles object-to-name conversion.
    """
    Name or identifier of the group to assign the user to.
    If an object with a `name` attribute is passed, `convert_group_to_name` extracts the name.
    """
    advanced: bool = False
    """Whether the user has access to advanced features. Defaults to False."""
    password: str  # Plaintext password, should be hashed by the service layer before storage.
    """The user's plaintext password for creation."""
    can_invite: bool = False
    """Permission to invite other users to their group. Defaults to False."""
    can_manage: bool = False
    """Permission to manage their group. Defaults to False."""
    can_organize: bool = False  # This permission's effect depends on application logic.
    """Permission for organizational tasks within their group. Defaults to False."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={  # Example for OpenAPI documentation
            "example": {
                "username": "NewUser",
                "fullName": "New User Name",
                "email": "newuser@example.com",
                "group": settings._DEFAULT_GROUP,  # Example uses default group name from settings
                "password": "aSecurePassword123",
                "admin": False,  # Example of boolean value
            }
        },
    )

    @field_validator("group", mode="before")
    @classmethod
    def convert_group_to_name(cls, v: Any, info: ValidationInfo) -> str | None:  # Added info, changed v type
        """
        Pydantic validator to ensure the 'group' field is a string (group name).

        If an object with a 'name' attribute (like a GroupRead schema) is passed
        for the 'group' field, this validator extracts the 'name' attribute.
        Otherwise, it returns the value as is (expecting it to be a string or None).

        Args:
            v (Any): The input value for the 'group' field.
            info (ValidationInfo): Pydantic validation context.

        Returns:
            str | None: The processed group name string, or None.
        """
        if v is None or isinstance(v, str):  # If already string or None, return
            return v
        try:
            # If `v` is an object with a `name` attribute (e.g., a Pydantic model for a group)
            return v.name
        except AttributeError:
            # If `v` is not a string and doesn't have a 'name' attribute, return as is for further validation.
            return v


class UserUpdate(UserCreate):
    """
    Schema likely used internally for saving a user to the database,
    ensuring required fields like `username`, `full_name`, and `password` are present.
    Extends `UserCreate`.
    """

    username: str  # Makes username mandatory for saving.
    full_name: str  # Makes full_name mandatory for saving.
    password: str  # Ensures password is part of the save payload (already in UserCreate).
    # Other fields inherited from UserCreate.


class UserRead(UserCreate):  # UserRead inheriting UserCreate (which has password) might be unintentional for a "Read" schema.
    """
    Schema for representing a user when read from the system.
    Extends `UserCreate` (which includes password), and adds system-generated fields
    like `id`, group details, and `cache_key`.

    NOTE: Inheriting from `UserCreate` means this schema will include `password`.
    For public user representations, `password` should typically be excluded.
    Consider having a different base or explicitly excluding password here if this
    is for general-purpose reading. `PrivateUser` below handles sensitive data.
    """

    id: UUID4
    """The unique identifier of the user."""
    group: str  # In UserCreate this was `str | None`. Here it's `str`. Might imply group is always resolved.
    """The name of the group the user belongs to."""
    group_id: UUID4
    """The unique identifier of the group the user belongs to."""
    group_slug: str  # Added based on original properties, likely from ORM.
    """The slug of the group the user belongs to."""
    # tokens: list[LongLiveTokenRead] | None = None # Commented out in original, might be populated conditionally.
    cache_key: str | None  # Made optional as per UserSQLModel default
    """A cache key associated with the user, potentially for ETag or client-side caching."""

    model_config = ConfigDict(from_attributes=True)

    @property
    def is_default_user(self) -> bool:
        """
        Computed property to check if this user is the default admin user,
        based on email matching the configured default email.
        """
        # Compares user's email (normalized) with the default email from settings (normalized).
        return self.email.strip().lower() == settings._DEFAULT_EMAIL.strip().lower()

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        """
        Provides SQLAlchemy loader options for optimizing `UserRead` queries.
        Eagerly loads the user's `group` and `tokens` relationships.
        """
        return [
            joinedload(UsersSQLModel.group),  # Eager load user's group
            joinedload(UsersSQLModel.tokens),  # Eager load user's API tokens
        ]


class UserSummary(_MarvinModel):
    """
    Schema for a summary representation of a user.
    Provides key identifying information, suitable for lists or brief displays.
    """

    id: UUID4
    """The unique identifier of the user."""
    group_id: UUID4
    """The unique identifier of the group the user belongs to."""
    username: str
    """The user's username."""
    full_name: str | None  # Made optional to match UserSQLModel
    """The user's full name."""
    model_config = ConfigDict(from_attributes=True)


class UserPagination(PaginationBase):
    """
    Schema for paginated responses containing a list of users.
    Items are expected to conform to the `UserRead` schema.
    """

    items: list[UserRead]
    """The list of users for the current page, serialized as `UserRead`."""


class UserSummaryPagination(PaginationBase):
    """
    Schema for paginated responses containing a list of user summaries.
    Items are expected to conform to the `UserSummary` schema.
    """

    items: list[UserSummary]
    """The list of user summaries for the current page."""


class PrivateUser(UserRead):  # Extends UserRead, so includes fields like password by inheritance.
    """
    Schema for representing a user with private or sensitive information,
    typically used internally or for the authenticated user themselves.
    Extends `UserRead` and adds fields like `password` (hashed), `login_attemps`,
    and `locked_at`.
    """

    password: str  # Hashed password. Inherited from UserRead -> UserCreate.
    """The user's hashed password (intended for internal use or when loading from DB)."""
    login_attemps: int = 0  # Renamed from login_attempts for consistency with model.
    """Number of failed login attempts. Defaults to 0."""
    locked_at: datetime | None = None
    """Timestamp (UTC) when the user account was locked. None if not locked."""

    model_config = ConfigDict(from_attributes=True)

    @field_validator("login_attemps", mode="before")
    @classmethod
    def none_to_zero(cls, v: int | None, info: ValidationInfo) -> int:  # Added info, corrected v type
        """
        Pydantic validator to ensure `login_attemps` defaults to 0 if None is provided.
        """
        return 0 if v is None else v

    @property
    def is_locked(self) -> bool:
        """
        Computed property to determine if the user account is currently locked.

        An account is considered locked if `locked_at` is set and the lockout duration
        (defined by `SECURITY_USER_LOCKOUT_TIME` setting) has not yet passed.
        """
        if self.locked_at is None:  # Not locked if locked_at is not set
            return False

        # Calculate when the lockout expires
        lockout_duration_hours = get_app_settings().SECURITY_USER_LOCKOUT_TIME
        lockout_expires_at = self.locked_at + timedelta(hours=lockout_duration_hours)

        # Compare with current UTC time
        return lockout_expires_at > datetime.now(UTC)

    def directory(self) -> Path:  # This method seems to imply a static method was intended or user-specific dir logic
        """
        Returns the directory path for this user.

        NOTE: This currently calls a non-existent static method `PrivateUser.get_directory(self.id)`.
        This suggests either `get_directory` should be a static/class method defined elsewhere
        and accessible here, or this logic needs to be implemented directly if it's simple
        path construction (e.g., based on user ID and a base data directory).
        Assuming it might be: `settings.DATA_DIR / "users" / str(self.id)`
        """
        # Placeholder for the actual implementation as get_directory is not defined.
        # Example: return get_app_settings().DATA_DIR / "user_files" / str(self.id)
        # For now, raising NotImplementedError or returning a placeholder.
        self.logger.warning("PrivateUser.directory() called but PrivateUser.get_directory() is not implemented.")
        # To avoid runtime error, let's return a conceptual path:
        return Path(f"/path/to/user/dirs/{self.id}")  # Placeholder path
        # raise NotImplementedError("PrivateUser.get_directory(user_id) is not defined.")

    @classmethod
    def loader_options(cls) -> list[LoaderOption]:
        """
        Provides SQLAlchemy loader options for optimizing `PrivateUser` queries.
        Eagerly loads the user's `group` and `tokens` relationships.
        """
        return [
            joinedload(UsersSQLModel.group),  # Eager load user's group
            joinedload(UsersSQLModel.tokens),  # Eager load user's API tokens
        ]


class LongLiveTokenRead_(TokenCreate):  # Underscore in name might indicate internal or special use.
    """
    Schema for reading a long-lived token, including the associated user's private details.
    Extends `TokenCreate` (which has `user_id`, `token`, `name`, `integration_id`).

    "Private" aspect likely comes from embedding the `PrivateUser` schema.
    The name `LongLiveTokenRead_` with a trailing underscore is unusual and might
    signify a specific internal purpose or differentiate it from another `LongLiveTokenRead`.
    """

    id: UUID4
    """The unique identifier of the API token."""
    user: PrivateUser  # Embeds the full PrivateUser object.
    """The user object associated with this token, including private details."""

    # Inherits user_id, token, name, integration_id from TokenCreate
    model_config = ConfigDict(from_attributes=True)
    # No loader_options here, but if this schema is built from an ORM LongLiveTokenSQLModel,
    # the query fetching that model might use `LongLiveTokenRead.loader_options()` to load the user.
