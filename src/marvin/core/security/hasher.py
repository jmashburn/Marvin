"""
This module provides password hashing functionality for the Marvin application.

It defines a `Hasher` protocol and provides two implementations:
- `BcryptHasher`: Uses bcrypt for strong password hashing.
- `FakeHasher`: A no-op hasher for testing purposes.

The `get_hasher` function returns the appropriate hasher based on the
application settings (FakeHasher for testing, BcryptHasher otherwise).
"""

from functools import lru_cache
from typing import Protocol

import bcrypt

from marvin.core.config import get_app_settings


class Hasher(Protocol):
    """
    Protocol defining the interface for password hashers.
    """

    def hash(self, password: str) -> str:
        """Hashes a password."""
        ...

    def verify(self, password: str, hashed: str) -> bool:
        """Verifies a password against a hashed version."""
        ...


class FakeHasher:
    """
    A fake hasher that does not perform any hashing.

    This is used for testing purposes.
    """

    def hash(self, password: str) -> str:
        """Returns the passwordそのまま."""
        return password

    def verify(self, password: str, hashed: str) -> bool:
        """Compares the password with the hashed value directly."""
        return password == hashed


class BcryptHasher:
    """
    A hasher that uses the bcrypt algorithm for password hashing.
    """

    def hash(self, password: str) -> str:
        """
        Hashes a password using bcrypt.

        Args:
            password (str): The password to hash.

        Returns:
            str: The hashed password.
        """
        password_bytes = password.encode("utf-8")
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        """
        Verifies a password against a bcrypt-hashed version.

        Args:
            password (str): The password to verify.
            hashed (str): The hashed password.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        password_bytes = password.encode("utf-8")
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)


@lru_cache(maxsize=1)
def get_hasher() -> Hasher:
    """
    Returns the appropriate password hasher based on application settings.

    If the application is in TESTING mode, a FakeHasher is returned.
    Otherwise, a BcryptHasher is returned.

    Returns:
        Hasher: The password hasher instance.
    """
    settings = get_app_settings()

    if settings.TESTING:
        return FakeHasher()

    return BcryptHasher()
