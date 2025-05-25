"""
This module defines the FastAPI controller for administrative "about" information
for the Marvin application.

It provides endpoints for administrators to retrieve general application details,
version information, configuration status, and basic statistics.
"""
from fastapi import APIRouter

from marvin.core.release_checker import get_latest_version
from marvin.core.settings.static import APP_VERSION # Current application version
from marvin.routes._base import BaseAdminController, controller # Base controller for admin routes
from marvin.schemas.admin.about import ( # Pydantic schemas for response models
    AdminAboutInfo,
    AppStatistics,
    CheckAppConfig,
)

# APIRouter for admin "about" section, prefixed with /about
# All routes in this controller will be under /admin/about due to AdminAPIRouter in main app and this prefix.
router = APIRouter(prefix="/about", tags=["Admin - About"])


@controller(router)
class AdminAboutController(BaseAdminController):
    """
    Controller for administrative endpoints providing information about the application.

    This includes version details, current configuration status (like SMTP, LDAP readiness),
    and basic application statistics (e.g., total users, groups).
    All endpoints require administrator privileges.
    """

    @router.get("", response_model=AdminAboutInfo, summary="Get Application Information")
    def get_app_info(self) -> AdminAboutInfo:
        """
        Retrieves general information about the application instance.

        This includes versioning, demo status, API configuration, database details,
        and feature enablement status for OIDC and OpenAI.
        Accessible only by administrators.

        Returns:
            AdminAboutInfo: A Pydantic model containing various application details.
        """
        settings = self.settings # Access application settings via base controller property

        # Construct and return the AdminAboutInfo response model
        return AdminAboutInfo(
            production=settings.PRODUCTION,
            version=APP_VERSION,
            versionLatest=get_latest_version(settings.GITHUB_VERSION_URL), # Fetches latest version from GitHub
            demo_status=settings.IS_DEMO,
            api_port=settings.API_PORT,
            api_docs=settings.API_DOCS,
            db_type=settings.DB_ENGINE,
            db_url=settings.DB_URL_PUBLIC, # Public (masked) database URL
            default_group=settings._DEFAULT_GROUP,
            allow_signup=settings.ALLOW_SIGNUP,
            build_id=settings.GIT_COMMIT_HASH, # Git commit hash for the build
            enable_oidc=settings.OIDC_AUTH_ENABLED,
            oidc_redirect=settings.OIDC_AUTO_REDIRECT,
            oidc_provider_name=settings.OIDC_PROVIDER_NAME,
            enable_openai=settings.OPENAI_ENABLED,
            enable_openai_image_services=settings.OPENAI_ENABLED and settings.OPENAI_ENABLE_IMAGE_SERVICES,
        )

    @router.get("/statistics", response_model=AppStatistics, summary="Get Application Statistics")
    def get_app_statistics(self) -> AppStatistics:
        """
        Retrieves basic statistics for the application.

        Currently includes the total number of users and groups.
        Accessible only by administrators.

        Returns:
            AppStatistics: A Pydantic model containing application statistics.
        """
        # Utilize repositories to fetch counts
        return AppStatistics(
            total_users=self.repos.users.count_all(),      # Total users in the system
            total_groups=self.repos.groups.count_all(),    # Total groups in the system
        )

    @router.get("/check", response_model=CheckAppConfig, summary="Check Application Configuration Status")
    def check_app_config(self) -> CheckAppConfig:
        """
        Checks and returns the status of various application configurations.

        This helps administrators understand if key features like email (SMTP),
        LDAP, OIDC, and OpenAI are properly configured and ready. It also checks
        if the application is up-to-date and if the base URL has been customized.
        Accessible only by administrators.

        Returns:
            CheckAppConfig: A Pydantic model indicating the readiness of different configurations.
        """
        settings = self.settings # Access application settings

        # Determine if the application is considered up-to-date.
        # 'develop' or 'nightly' versions are always considered "up-to-date" for this check.
        # Otherwise, compare current APP_VERSION with the latest fetched version.
        is_up_to_date_status = (
            APP_VERSION in ["develop", "nightly"] or 
            get_latest_version(settings.GITHUB_VERSION_URL) == APP_VERSION
        )

        return CheckAppConfig(
            email_ready=settings.SMTP_ENABLED,  # SMTP (email) configured and enabled
            ldap_ready=settings.LDAP_ENABLED,   # LDAP configured and enabled
            base_url_set=settings.BASE_URL != "http://localhost:8080", # Base URL customized from default
            is_up_to_date=is_up_to_date_status, # Application version is current
            oidc_ready=settings.OIDC_READY,     # OIDC configured and ready
            enable_openai=settings.OPENAI_ENABLED, # OpenAI configured and enabled
        )
