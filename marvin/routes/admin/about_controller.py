from fastapi import APIRouter

from marvin.core.release_checker import get_latest_version
from marvin.core.settings.static import APP_VERSION
from marvin.routes._base import BaseAdminController, controller
from marvin.schemas.admin.about import AdminAboutInfo, AppStatistics, CheckAppConfig

router = APIRouter(prefix="/about")


@controller(router)
class AdminAboutController(BaseAdminController):
    @router.get("", response_model=AdminAboutInfo)
    def get_app_info(self):
        """Get general application information"""

        settings = self.settings

        return AdminAboutInfo(
            production=settings.PRODUCTION,
            version=APP_VERSION,
            versionLatest=get_latest_version(),
            demo_status=settings.IS_DEMO,
            api_port=settings.API_PORT,
            api_docs=settings.API_DOCS,
            db_type=settings.DB_ENGINE,
            db_url=settings.DB_URL_PUBLIC,
            default_group=settings.DEFAULT_GROUP,
            default_household=settings.DEFAULT_HOUSEHOLD,
            allow_signup=settings.ALLOW_SIGNUP,
            build_id=settings.GIT_COMMIT_HASH,
            enable_oidc=settings.OIDC_AUTH_ENABLED,
            oidc_redirect=settings.OIDC_AUTO_REDIRECT,
            oidc_provider_name=settings.OIDC_PROVIDER_NAME,
            enable_openai=settings.OPENAI_ENABLED,
            enable_openai_image_services=settings.OPENAI_ENABLED and settings.OPENAI_ENABLE_IMAGE_SERVICES,
        )

    @router.get("/statistics", response_model=AppStatistics)
    def get_app_statistics(self):
        return AppStatistics(
            total_users=self.repos.users.count_all(),
            total_groups=self.repos.groups.count_all(),
        )

    @router.get("/check", response_model=CheckAppConfig)
    def check_app_config(self):
        settings = self.settings

        return CheckAppConfig(
            email_ready=settings.SMTP_ENABLE,
            ldap_ready=settings.LDAP_ENABLED,
            base_url_set=settings.BASE_URL != "http://localhost:8080",
            is_up_to_date=APP_VERSION == "develop" or APP_VERSION == "nightly" or get_latest_version() == APP_VERSION,
            oidc_ready=settings.OIDC_READY,
            enable_openai=settings.OPENAI_ENABLED,
        )
