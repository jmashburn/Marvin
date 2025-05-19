from datetime import timedelta

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm.session import Session
from starlette.datastructures import URLPath

from marvin.core import root_logger, security
from marvin.core.config import get_app_settings
from marvin.core.dependencies import get_current_user
from marvin.core.exceptions import MissingClaimException, UserLockedOut
from marvin.core.security.providers.openid_provider import OpenIDProvider
from marvin.core.security.security import get_auth_provider
from marvin.db.db_setup import generate_session
from marvin.routes._base.routers import UserAPIRouter
from marvin.schemas.user import PrivateUser
from marvin.schemas.user.auth import CredentialsRequestForm


from marvin.services.event_bus_service.event_types import EventTypes, EventTokenRefreshData
from marvin.services.event_bus_service.event_bus_service import EventBusService

public_router = APIRouter(tags=["Users: Authentication"])
user_router = UserAPIRouter(tags=["Users: Authentication"])
logger = root_logger.get_logger("auth")

remember_me_duration = timedelta(days=14)

settings = get_app_settings()
if settings.OIDC_READY | False:
    oauth = OAuth()
    scope = None
    if settings.OIDC_SCOPES_OVERRIDE:
        scope = settings.OIDC_SCOPES_OVERRIDE
    else:
        groups_claim = settings.OIDC_GROUPS_CLAIM if settings.OIDC_REQUIRES_GROUP_CLAIM else ""
        scope = f"openid email profile {groups_claim}"
    client_args = {"scope": scope.rstrip()}
    if settings.OIDC_TLS_CACERTFILE:
        client_args["verify"] = settings.OIDC_TLS_CACERTFILE

    oauth.register(
        "oidc",
        client_id=settings.OIDC_CLIENT_ID,
        client_secret=settings.OIDC_CLIENT_SECRET,
        server_metadata_url=settings.OIDC_CONFIGURATION_URL,
        client_kwargs=client_args,
        code_challenge_method="S256",
    )


class MarvinAuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"

    @classmethod
    def respond(cls, token: str, token_type: str = "bearer") -> dict:
        return cls(access_token=token, token_type=token_type).model_dump()


@public_router.post("/token")
def get_token(
    request: Request,
    response: Response,
    data: CredentialsRequestForm = Depends(),
    session: Session = Depends(generate_session),
):
    if "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"]
        if "," in ip:  # if there are multiple IPs, the first one is canonically the true client
            ip = str(ip.split(",")[0])
    else:
        # request.client should never be null, except sometimes during testing
        ip = request.client.host if request.client else "unknown"

    try:
        auth_provider = get_auth_provider(session, data)
        auth = auth_provider.authenticate()
    except UserLockedOut as e:
        logger.error(f"User is locked out from {ip}")
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="User is locked out") from e

    if not auth:
        logger.error(f"Incorrect username or password from {ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    access_token, duration = auth

    expires_in = duration.total_seconds() if duration else None
    response.set_cookie(
        key="marvin.access_token",
        value=access_token,
        httponly=True,
        max_age=expires_in,
        secure=settings.PRODUCTION,
    )

    return MarvinAuthToken.respond(access_token)


@public_router.get("/oauth")
async def oauth_login(request: Request):
    if not oauth:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not initialize OAuth client",
        )
    client = oauth.create_client("oidc")
    redirect_url = None
    if not settings.PRODUCTION:
        # in development, we want to redirect to the frontend
        redirect_url = "http://localhost:3000/login"
    else:
        redirect_url = URLPath("/login").make_absolute_url(request.base_url)

    response: RedirectResponse = await client.authorize_redirect(request, redirect_url)
    return response


@public_router.get("/oauth/callback")
async def oauth_callback(request: Request, response: Response, session: Session = Depends(generate_session)):
    if not oauth:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not initialize OAuth client",
        )
    client = oauth.create_client("oidc")

    token = await client.authorize_access_token(request)

    auth = None
    try:
        auth_provider = OpenIDProvider(session, token["userinfo"])
        auth = auth_provider.authenticate()
    except MissingClaimException:
        try:
            logger.debug("[OIDC] Claims not present in the ID token, pulling user info")
            userinfo = await client.userinfo(token=token)
            auth_provider = OpenIDProvider(session, userinfo)
            auth = auth_provider.authenticate()
        except MissingClaimException:
            auth = None

    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    access_token, duration = auth

    expires_in = duration.total_seconds() if duration else None

    response.set_cookie(
        key="marvin.access_token",
        value=access_token,
        httponly=True,
        max_age=expires_in,
        secure=settings.PRODUCTION,
    )

    return MarvinAuthToken.respond(access_token)


@user_router.get("/refresh", response_model=MarvinAuthToken)
async def refresh_token(current_user: PrivateUser = Depends(get_current_user)):
    """Use a valid token to get another token"""
    access_token = security.create_access_token(data={"sub": str(current_user.id)})

    event_bus = EventBusService()
    event_bus.dispatch(
        integration_id="token_refresh",
        event_type=EventTypes.data_export,
        group_id=current_user.group_id,
        document_data=EventTokenRefreshData(username=current_user.username, token=access_token),
        message="App Info",
    )

    return MarvinAuthToken.respond(access_token)


@user_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("marvin.access_token")
    return {"message": "Logged out"}
