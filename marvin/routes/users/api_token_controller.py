from datetime import timedelta

from fastapi import HTTPException, status

from marvin.core.security import create_access_token
from marvin.routes._base import BaseUserController, controller
from marvin.routes._base.routers import UserAPIRouter
from marvin.schemas.user import (
    LongLiveTokenCreateResponse,
    LongLiveTokenRead,
    LongLiveTokenCreate,
    TokenResponseDelete,
    TokenCreate,
)

router = UserAPIRouter(prefix="/users", tags=["Users: Tokens"])


@controller(router)
class UserApiTokensController(BaseUserController):
    @router.post("/api-tokens", status_code=status.HTTP_201_CREATED, response_model=LongLiveTokenCreateResponse)
    def create_api_token(
        self,
        token_params: LongLiveTokenCreate,
    ):
        """Create api_token in the Database"""

        token_data = {
            "long_token": True,
            "id": str(self.user.id),
            "name": token_params.name,
            "integration_id": token_params.integration_id,
        }

        five_years = timedelta(1825)
        token = create_access_token(token_data, five_years)

        token_model = TokenCreate(
            name=token_params.name,
            token=token,
            user_id=self.user.id,
            integration_id=token_params.integration_id,
        )

        new_token_in_db = self.repos.api_tokens.create(token_model)

        if new_token_in_db:
            return new_token_in_db

    @router.delete("/api-tokens/{token_id}", response_model=TokenResponseDelete)
    def delete_api_token(self, token_id: int):
        """Delete api_token from the Database"""
        token: LongLiveTokenRead = self.repos.api_tokens.get_one(token_id)

        if not token:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Could not locate token with id '{token_id}' in database")

        if token.user.email == self.user.email:
            deleted_token = self.repos.api_tokens.delete(token_id)
            return TokenResponseDelete(token_delete=deleted_token.name)
        else:
            raise HTTPException(status.HTTP_403_FORBIDDEN)
