"""
This module provides functions for initializing default and development users
in the Marvin application.

It includes utilities to:
- Define data for a set of development users.
- Create a default administrative user.
- Conditionally create development users if the application is not in production mode.
"""
from marvin.core import root_logger
from marvin.core.config import get_app_settings
from marvin.core.security import hash_password # For hashing default passwords
from marvin.repos.repository_factory import AllRepositories

# Logger for this module
logger = root_logger.get_logger("init_users")
# Application settings instance
settings = get_app_settings()


def dev_users() -> list[dict]:
    """
    Provides a list of predefined user data for development and testing purposes.

    Each user dictionary contains necessary information like full name, username,
    email, a hashed default password, group assignment, and admin status (False).

    Returns:
        list[dict]: A list of dictionaries, where each dictionary represents a
                    development user's data.
    """
    return [
        {
            "full_name": "Jason",
            "username": "jason",
            "email": "jason@example.com",
            "password": hash_password(settings._DEFAULT_PASSWORD), # Use hashed default password
            "group": settings._DEFAULT_GROUP, # Assign to default group
            "admin": False,
        },
        {
            "full_name": "Bob",
            "username": "bob",
            "email": "bob@example.com",
            "password": hash_password(settings._DEFAULT_PASSWORD),
            "group": settings._DEFAULT_GROUP,
            "admin": False,
        },
        {
            "full_name": "Sarah",
            "username": "sarah",
            "email": "sarah@example.com",
            "password": hash_password(settings._DEFAULT_PASSWORD),
            "group": settings._DEFAULT_GROUP,
            "admin": False,
        },
        {
            "full_name": "Sammy",
            "username": "sammy",
            "email": "sammy@example.com",
            "password": hash_password(settings._DEFAULT_PASSWORD),
            "group": settings._DEFAULT_GROUP,
            "admin": False,
        },
    ]


def default_user_init(db: AllRepositories) -> None:
    """
    Initializes the default administrative user and, if not in production,
    creates additional development users.

    The default admin user is created with credentials specified in the application
    settings (e.g., `settings._DEFAULT_EMAIL`, `settings._DEFAULT_PASSWORD`).
    Development users are sourced from the `dev_users()` function.

    Args:
        db (AllRepositories): An instance of `AllRepositories` providing access
                              to the users repository for creating users.
    """
    # Define the default administrative user's data
    default_user = {
        "full_name": "Change Me", # Default full name, intended to be changed
        "username": "admin",      # Default admin username
        "email": settings._DEFAULT_EMAIL,
        "password": hash_password(settings._DEFAULT_PASSWORD),
        "group": settings._DEFAULT_GROUP, # Assign to the default group
        "admin": True, # This user is an administrator
    }

    logger.info("Generating Default User")
    # Create the default admin user using the users repository
    db.users.create(default_user)

    # If the application is not in production mode, create development users
    if not settings.PRODUCTION:
        logger.info("Non-production environment detected, creating development users.")
        for user_data in dev_users():
            db.users.create(user_data)
