from abc import ABC

from sqlalchemy.orm import Session
from pydantic import UUID4, ConfigDict
from fastapi import Depends, HTTPException
from logging import Logger


from marvin.core.config import get_app_dirs, get_app_settings
from marvin.db.db_setup import generate_session
from marvin.core.settings import AppSettings
from marvin.core.settings.directories import AppDirectories
from marvin.core.root_logger import get_logger
from marvin.repos.all_repositories import AllRepositories
from marvin.core.dependencies import get_current_user, get_admin_user
from marvin.schemas.user import PrivateUser
from marvin.routes._base.checks import OperationChecks
from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import EventTypes, EventDocumentDataBase


class _BaseController(ABC):
    session: Session = Depends(generate_session)

    _repos: AllRepositories | None = None
    _settings: AppSettings | None = None
    _directories: AppDirectories | None = None
    _logger: Logger | None = None

    @property
    def repos(self) -> AllRepositories:
        if not self._repos:
            self._repos = AllRepositories(self.session)
        return self._repos

    @property
    def settings(self) -> AppSettings:
        if not self._settings:
            self._settings = get_app_settings()
        return self._settings

    @property
    def directories(self) -> AppDirectories:
        if not self._directories:
            self._directories = get_app_dirs()
        return self._directories

    @property
    def logger(self) -> Logger:
        if not self._logger:
            self._logger = get_logger()
        return self._logger

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BasePublicController(_BaseController):
    pass


class BaseUserController(_BaseController):
    user: PrivateUser = Depends(get_current_user)

    _checks: OperationChecks

    def __init__(self, user_id: UUID4, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = user_id

    def get_user(self):
        user = self.repos.user.get_by_id(self.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user


class BaseAdminController(BaseUserController):
    user: PrivateUser = Depends(get_admin_user)

    @property
    def repos(self) -> AllRepositories:
        if not self._repos:
            self._repos = AllRepositories(self.session)
        return self._repos


class BaseCrudController(BaseUserController):
    event_bus: EventBusService = Depends(EventBusService.as_dependency)

    def publish_event(
        self,
        event_type: EventTypes,
        document_data: EventDocumentDataBase,
        message: str = "",
    ) -> None:
        self.event_bus.dispatch(
            event_type=event_type,
            document_data=document_data,
            message=message,
        )
