from abc import ABC
from logging import Logger

from fastapi import Depends, HTTPException
from pydantic import UUID4, ConfigDict
from sqlalchemy.orm import Session

from marvin.core.exceptions import registered_exceptions

from marvin.core.config import get_app_dirs, get_app_settings
from marvin.core.dependencies import get_admin_user, get_current_user
from marvin.core.root_logger import get_logger
from marvin.core.settings import AppSettings
from marvin.core.settings.directories import AppDirectories
from marvin.db.db_setup import generate_session
from marvin.repos.all_repositories import AllRepositories
from marvin.routes._base.checks import OperationChecks
from marvin.schemas.user import PrivateUser
from marvin.schemas.group import GroupRead
from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import EventDocumentDataBase, EventTypes
from marvin.repos._utils import NotSet, NOT_SET


class _BaseController(ABC):
    session: Session = Depends(generate_session)

    _repos: AllRepositories | None = None
    _settings: AppSettings | None = None
    _directories: AppDirectories | None = None
    _logger: Logger | None = None

    @property
    def repos(self) -> AllRepositories:
        if not self._repos:
            self._repos = AllRepositories(self.session, group_id=self.group_id)
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

    @property
    def group_id(self) -> UUID4 | None | NotSet:
        return NOT_SET

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BasePublicController(_BaseController):
    pass


class BaseUserController(_BaseController):
    user: PrivateUser = Depends(get_current_user)

    _checks: OperationChecks

    def registered_exceptions(self, ex: type[Exception]) -> str:
        registered = {
            **registered_exceptions(),
        }
        return registered.get(ex, "An unexpected error occurred")

    @property
    def group_id(self) -> UUID4:
        return self.user.group_id

    @property
    def group(self) -> GroupRead:
        return self.repos.groups.get_one(self.group_id)

    @property
    def checks(self) -> OperationChecks:
        if not self._checks:
            self._checks = OperationChecks(self.user)
        return self._checks


class BaseAdminController(BaseUserController):
    user: PrivateUser = Depends(get_admin_user)

    @property
    def repos(self) -> AllRepositories:
        if not self._repos:
            self._repos = AllRepositories(self.session, group_id=None)
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
