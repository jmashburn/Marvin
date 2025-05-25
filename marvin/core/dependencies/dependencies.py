import tempfile
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import fastapi
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError
from sqlalchemy.orm.session import Session

from marvin.core import root_logger
from marvin.core.config import get_app_dirs, get_app_settings
from marvin.db.db_setup import generate_session
from marvin.repos.all_repositories import get_repositories
from marvin.schemas.group import GroupRead
from marvin.schemas.user import PrivateUser, TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
oauth2_scheme_soft_fail = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)
ALGORITHM = "HS256"
app_dirs = get_app_dirs()
settings = get_app_settings()
logger = root_logger.get_logger("dependencies")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def is_logged_in(token: str = Depends(oauth2_scheme_soft_fail), session=Depends(generate_session)) -> bool:
    """
    When you need to determine if the user is logged in, but don't need the user, you can use this
    function to return a boolean value to represent if the user is logged in. No Auth exceptions are raised
    if the user is not logged in. This behavior is not the same as 'get_current_user'

    Args:
        token (str, optional): [description]. Defaults to Depends(oauth2_scheme_soft_fail).
        session ([type], optional): [description]. Defaults to Depends(generate_session).

    Returns:
        bool: True = Valid User / False = Not User
    """
    try:
        payload = jwt.decode(token, settings.SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        long_token: str = payload.get("long_token")

        if long_token is not None:
            try:
                if validate_long_live_token(session, token, payload.get("id")):
                    return True
            except Exception:
                return False

        return user_id is not None

    except Exception:
        return False


async def get_public_group(group_slug: str = fastapi.Path(...), session=Depends(generate_session)) -> GroupRead:
    """
    FastAPI dependency to get a public group by its slug.

    Args:
        group_slug (str): The slug of the group.
        session: SQLAlchemy session dependency.

    Raises:
        HTTPException: If the group is not found or is private.

    Returns:
        GroupRead: The public group.
    """
    repos = get_repositories(session)
    group = repos.groups.get_by_slug_or_id(group_slug)

    if not group or group.preferences.private_group:
        raise HTTPException(404, "group not found")
    else:
        return group


async def try_get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme_soft_fail),
    session=Depends(generate_session),
) -> PrivateUser | None:
    """
    FastAPI dependency to try to get the current user.

    This dependency will not raise an exception if the user is not authenticated.

    Args:
        request (Request): The FastAPI request object.
        token (str, optional): The OAuth2 token. Defaults to Depends(oauth2_scheme_soft_fail).
        session: SQLAlchemy session dependency.

    Returns:
        PrivateUser | None: The current user if authenticated, otherwise None.
    """
    try:
        return await get_current_user(request, token, session)
    except Exception:
        return None


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme_soft_fail),
    session=Depends(generate_session),
) -> PrivateUser:
    """
    FastAPI dependency to get the current authenticated user.

    It tries to get the token from the Authorization header or a cookie.

    Args:
        request (Request): The FastAPI request object.
        token (str | None, optional): The OAuth2 token. Defaults to Depends(oauth2_scheme_soft_fail).
        session: SQLAlchemy session dependency.

    Raises:
        HTTPException: If the user is not authenticated or the token is invalid.

    Returns:
        PrivateUser: The authenticated user.
    """
    if token is None and "marvin.access_token" in request.cookies:
        # Try extract from cookie
        token = request.cookies.get("marvin.access_token", "")
    else:
        token = token or ""

    try:
        payload = jwt.decode(token, settings.SECRET, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        long_token: str | None = payload.get("long_token")

        if long_token is not None:
            return validate_long_live_token(session, token, payload.get("id"))

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(user_id=user_id)
    except PyJWTError as e:
        raise credentials_exception from e

    repos = get_repositories(session, group_id=None)

    user = repos.users.get_one(token_data.user_id, "id", any_case=False)

    # If we don't commit here, lazy-loads from user relationships will leave some table lock in postgres
    # which can cause quite a bit of pain further down the line
    session.commit()
    if user is None:
        raise credentials_exception
    return user


async def get_integration_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    FastAPI dependency to get the integration ID from the token.

    Args:
        token (str): The OAuth2 token. Defaults to Depends(oauth2_scheme).

    Raises:
        HTTPException: If the token is invalid.

    Returns:
        str: The integration ID.
    """
    try:
        decoded_token = jwt.decode(token, settings.SECRET, algorithms=[ALGORITHM])
        return decoded_token.get("integration_id", DEFAULT_INTEGRATION_ID)

    except PyJWTError as e:
        raise credentials_exception from e


async def get_admin_user(current_user: PrivateUser = Depends(get_current_user)) -> PrivateUser:
    """
    FastAPI dependency to ensure the current user is an admin.

    Args:
        current_user (PrivateUser): The current authenticated user. Defaults to Depends(get_current_user).

    Raises:
        HTTPException: If the user is not an admin.

    Returns:
        PrivateUser: The admin user.
    """
    if not current_user.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return current_user


def validate_long_live_token(session: Session, client_token: str, user_id: str) -> PrivateUser:
    """
    Validates a long-lived API token.

    Args:
        session (Session): SQLAlchemy session.
        client_token (str): The token provided by the client.
        user_id (str): The user ID associated with the token.

    Raises:
        HTTPException: If the token is invalid or not found.

    Returns:
        PrivateUser: The user associated with the token.
    """
    repos = get_repositories(session, group_id=None)

    token = repos.api_tokens.multi_query({"token": client_token, "user_id": user_id})

    try:
        return token[0].user
    except IndexError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED) from e


def validate_file_token(token: str | None = None) -> Path:
    """
    Args:
        token (Optional[str], optional): _description_. Defaults to None.

    Raises:
        HTTPException: 400 Bad Request when no token or the file doesn't exist
        HTTPException: 401 Unauthorized when the token is invalid
    """
    if not token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    try:
        payload = jwt.decode(token, settings.SECRET, algorithms=[ALGORITHM])
        file_path = Path(payload.get("file"))
    except PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="could not validate file token",
        ) from e

    if not file_path.exists():
        raise HTTPException(status.HTTP_400_BAD_REQUEST)

    return file_path


@contextmanager
def get_temporary_zip_path(auto_unlink=True) -> Generator[Path, None, None]:
    """
    Context manager to get a temporary path for a zip file.

    Args:
        auto_unlink (bool, optional): Whether to automatically delete the file on exit. Defaults to True.

    Yields:
        Generator[Path, None, None]: The path to the temporary zip file.
    """
    app_dirs.TEMP_DIR.mkdir(exist_ok=True, parents=True)
    temp_path = app_dirs.TEMP_DIR.joinpath("my_zip_archive.zip")
    try:
        yield temp_path
    finally:
        if auto_unlink:
            temp_path.unlink(missing_ok=True)


@contextmanager
def get_temporary_path(auto_unlink=True) -> Generator[Path, None, None]:
    """
    Context manager to get a temporary directory path.

    Args:
        auto_unlink (bool, optional): Whether to automatically delete the directory on exit. Defaults to True.

    Yields:
        Generator[Path, None, None]: The path to the temporary directory.
    """
    temp_path = app_dirs.TEMP_DIR.joinpath(uuid4().hex)
    temp_path.mkdir(exist_ok=True, parents=True)
    try:
        yield temp_path
    finally:
        if auto_unlink:
            rmtree(temp_path)


def temporary_file(ext: str = "") -> Callable[[], Generator[tempfile._TemporaryFileWrapper, None, None]]:
    """
    Returns a context manager that yields a temporary file with the specified extension.

    The file is created in the application's temporary directory and is deleted on exit.

    Args:
        ext (str, optional): The file extension. Defaults to "".

    Returns:
        Callable[[], Generator[tempfile._TemporaryFileWrapper, None, None]]: A context manager function.
    """

    def func():
        temp_path = app_dirs.TEMP_DIR.joinpath(uuid4().hex + ext)
        temp_path.touch()

        with tempfile.NamedTemporaryFile(mode="w+b", suffix=ext) as f:
            try:
                yield f
            finally:
                temp_path.unlink(missing_ok=True)

    return func
