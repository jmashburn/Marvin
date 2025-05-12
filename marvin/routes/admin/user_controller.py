from functools import cached_property

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4

from marvin.core import security
from marvin.routes._base import BaseAdminController, controller
from marvin.routes._base.mixins import HttpRepo
from marvin.schemas.response.pagination import PaginationQuery
from marvin.schemas.response.responses import ErrorResponse
from marvin.schemas.user.auth import UnlockResults
from marvin.schemas.user import UserCreate, UserRead, UserPagination
from marvin.schemas.user.password import ForgotPassword, PasswordResetToken
from marvin.services.user.password_reset_service import PasswordResetService
from marvin.services.user.user_service import UserService

router = APIRouter(prefix="/users")


@controller(router)
class AdminUserManagementRoutes(BaseAdminController):
    @cached_property
    def repo(self):
        return self.repos.users

    # =======================================================================
    # CRUD Operations

    @property
    def mixins(self):
        return HttpRepo[UserCreate, UserRead, UserRead](self.repo, self.logger, self.registered_exceptions)

    @router.get("", response_model=UserPagination)
    def get_all(self, q: PaginationQuery = Depends(PaginationQuery)):
        response = self.repo.page_all(
            pagination=q,
            override=UserRead,
        )

        response.set_pagination_guides(router.url_path_for("get_all"), q.model_dump())
        return response

    @router.post("", response_model=UserRead, status_code=201)
    def create_one(self, data: UserCreate):
        data.password = security.hash_password(data.password)
        return self.mixins.create_one(data)

    @router.post("/unlock", response_model=UnlockResults)
    def unlock_users(self, force: bool = False) -> UnlockResults:
        user_service = UserService(self.repos)
        unlocked = user_service.reset_locked_users(force=force)

        return UnlockResults(unlocked=unlocked)

    @router.get("/{item_id}", response_model=UserRead)
    def get_one(self, item_id: UUID4):
        return self.mixins.get_one(item_id)

    @router.put("/{item_id}", response_model=UserRead)
    def update_one(self, item_id: UUID4, data: UserRead):
        # Prevent self demotion
        if self.user.id == item_id and self.user.admin != data.admin:
            raise HTTPException(status_code=403, detail=ErrorResponse.respond("you cannot demote yourself"))

        return self.mixins.update_one(data, item_id)

    @router.delete("/{item_id}", response_model=UserRead)
    def delete_one(self, item_id: UUID4):
        return self.mixins.delete_one(item_id)

    @router.post("/password-reset-token", response_model=PasswordResetToken, status_code=201)
    def generate_token(self, email: ForgotPassword):
        """Generates a reset token and returns it. This is an authenticated endpoint"""
        f_service = PasswordResetService(self.session)
        token_entry = f_service.generate_reset_token(email.email)
        if not token_entry:
            raise HTTPException(status_code=500, detail=ErrorResponse.respond("error while generating reset token"))
        return PasswordResetToken(token=token_entry.token)
