from fastapi import Depends, HTTPException, status
from pydantic import UUID4

from datetime import timedelta

from marvin.core.security import hash_password, create_access_token
from marvin.core.security.providers.credentials_provider import CredentialsProvider
from marvin.db.models.users.users import AuthMethod
from marvin.routes._base import BaseAdminController, BaseUserController, controller
from marvin.routes._base.mixins import HttpRepo
from marvin.routes._base.routers import AdminAPIRouter, UserAPIRouter
from marvin.routes.users._helpers import assert_user_change_allowed
from marvin.schemas.response import ErrorResponse, SuccessResponse
from marvin.schemas.response.pagination import PaginationQuery
from marvin.schemas.user import (
    ChangePassword,
    UserCreate,
    UserRead,
    LongLiveTokenCreate,
    LongLiveTokenRead,
    LongLiveTokenRead_,
    TokenResponseDelete,
    TokenCreate,
    LongLiveTokenCreateResponse,
)
from marvin.schemas.user.user import UserPagination

user_router = UserAPIRouter(prefix="/users", tags=["Users: CRUD"])
admin_router = AdminAPIRouter(prefix="/users", tags=["Users: Admin CRUD"])

from marvin.services.event_bus_service.event_bus_service import EventBusService
from marvin.services.event_bus_service.event_types import EventTypes, EventUserSignupData
from marvin.services.user.registration_service import RegistrationService


# @controller(admin_router)
# class AdminUserController(BaseAdminController):
#     @property
#     def mixins(self) -> HttpRepo:
#         return HttpRepo[UserIn, UserRead, UserCreate](self.repos.users, self.logger)

#     @admin_router.get("", response_model=UserPagination)
#     def get_all(self, q: PaginationQuery = Depends(PaginationQuery)):
#         """Returns all users from all groups"""

#         response = self.repos.users.page_all(
#             pagination=q,
#             override=UserRead,
#         )

#         response.set_pagination_guides(admin_router.url_path_for("get_all"), q.model_dump())
#         return response

#     @admin_router.post("", response_model=UserRead, status_code=201)
#     def create_user(self, new_user: UserCreate):
#         new_user.password = hash_password(new_user.password)
#         return self.mixins.create_one(new_user)

#     @admin_router.get("/{item_id}", response_model=UserRead)
#     def get_user(self, item_id: UUID4):
#         return self.mixins.get_one(item_id)

#     @admin_router.delete("/{item_id}")
#     def delete_user(self, item_id: UUID4):
#         self.mixins.delete_one(item_id)


@controller(user_router)
class UserController(BaseUserController):
    @user_router.get("/self", response_model=UserRead)
    def get_logged_in_user(self):
        return self.user

    @user_router.put("/password")
    def update_password(self, password_change: ChangePassword):
        """Resets the User Password"""
        if self.user.password == "LDAP" or self.user.auth_method == AuthMethod.LDAP:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorResponse.respond("User password is managed by LDAP"))
        if not CredentialsProvider.verify_password(password_change.current_password, self.user.password):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, ErrorResponse.respond("User password is incorrect"))

        self.user.password = hash_password(password_change.new_password)
        try:
            self.repos.users.update_password(self.user.id, self.user.password)
        except Exception as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                ErrorResponse.respond("Failed to update password"),
            ) from e

        return SuccessResponse.respond("User password updated successfully")

    @user_router.put("/{item_id}")
    def update_user(self, item_id: UUID4, new_data: UserRead):
        assert_user_change_allowed(item_id, self.user, new_data)

        try:
            self.repos.users.update(item_id, new_data.model_dump())
        except Exception as e:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                ErrorResponse.respond("Failed to update user"),
            ) from e

        return SuccessResponse.respond("User updated successfully")


# @controller(user_router)
# class UserApiTokensController(BaseUserController):
#     @user_router.post("/api-tokens", status_code=status.HTTP_201_CREATED, response_model=LongLiveTokenCreateResponse)
#     def create_api_token(self, token_params: LongLiveTokenCreate):
#         """Create api_token in the Database"""
#         token_data = {
#             "long_token": True,
#             "id": str(self.user.id),
#             "name": token_params.name,
#             "integration_id": token_params.integration_id,
#         }

#         five_years = timedelta(1825)
#         token = create_access_token(token_data, five_years)

#         token_model = TokenCreate(
#             name=token_params.name,
#             token=token,
#             user_id=self.user.id,
#         )

#         new_token_in_db = self.repos.api_tokens.create(token_model)

#         print(new_token_in_db)

#         if new_token_in_db:
#             return new_token_in_db

#     @user_router.delete("/api-tokens/{token_id}", response_model=TokenResponseDelete)
#     def delete_api_token(self, token_id: UUID4):
#         """Delete api_token from the Database"""
#         token: LongLiveTokenRead_ = self.repos.api_tokens.get_one(token_id)

#         if not token:
#             raise HTTPException(status.HTTP_404_NOT_FOUND, f"Could not locate token with id '{token_id}' in database")

#         if token.user.email == self.user.email:
#             deleted_token = self.repos.api_tokens.delete(token_id)
#             return TokenResponseDelete(token_delete=deleted_token.name)
#         else:
#             raise HTTPException(status.HTTP_403_FORBIDDEN)
