"""
This module provides core security functionalities for the Marvin application.

It includes functions for:
- Authentication provider selection (LDAP or credentials-based).
- Access token creation (JWT).
- File-specific token creation.
- Password hashing.
- Generation of URL-safe tokens.
"""

import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
from sqlalchemy.orm.session import Session

from marvin.core import root_logger
from marvin.core.config import get_app_settings
from marvin.core.security.hasher import get_hasher
from marvin.core.security.providers.auth_providers import AuthProvider
from marvin.core.security.providers.credentials_provider import CredentialsProvider
from marvin.core.security.providers.ldap_provider import LDAPProvider
from marvin.schemas.user.auth import CredentialsRequest, CredentialsRequestForm

ALGORITHM = "HS256"

logger = root_logger.get_logger("security")


def get_auth_provider(session: Session, data: CredentialsRequestForm) -> AuthProvider:
    """
    Returns the appropriate authentication provider based on application settings.

    If LDAP is enabled in settings, it returns an LDAPProvider.
    Otherwise, it returns a CredentialsProvider.

    Args:
        session (Session): SQLAlchemy session.
        data (CredentialsRequestForm): The credentials request form data.

    Returns:
        AuthProvider: The selected authentication provider.
    """
    settings = get_app_settings()

    credentials_request = CredentialsRequest(**data.__dict__)
    if settings.LDAP_ENABLED:
        return LDAPProvider(session, credentials_request)

    return CredentialsProvider(session, credentials_request)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates a JWT access token.

    Args:
        data (dict): The data to include in the token payload.
        expires_delta (timedelta | None, optional): The token expiration time.
            Defaults to the value specified in application settings.

    Returns:
        str: The encoded JWT access token.
    """
    settings = get_app_settings()

    to_encode = data.copy()
    expires_delta = expires_delta or timedelta(hours=settings.TOKEN_TIME)

    expire = datetime.now(UTC) + expires_delta

    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET, algorithm=ALGORITHM)


def create_file_token(file_path: Path) -> str:
    """
    Creates a short-lived JWT access token specifically for accessing a file.

    Args:
        file_path (Path): The path to the file.

    Returns:
        str: The encoded JWT file access token.
    """
    token_data = {"file": str(file_path)}
    return create_access_token(token_data, expires_delta=timedelta(minutes=30))


def hash_password(password: str) -> str:
    """Takes in a raw password and hashes it. Used prior to saving a new password to the database."""
    return get_hasher().hash(password)


def url_safe_token() -> str:
    """Generates a cryptographic token without embedded data. Used for password reset tokens and invitation tokens"""
    return secrets.token_urlsafe(24)
