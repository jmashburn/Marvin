from marvin.schemas._marvin import _MarvinModel


class AppStatistics(_MarvinModel):
    pass


class AppInfo(_MarvinModel):
    production: bool
    version: str


class AppTheme(_MarvinModel):
    light_primary: str = "#E58325"
    light_accent: str = "#007A99"
    light_secondary: str = "#973542"
    light_success: str = "#43A047"
    light_info: str = "#1976D2"
    light_warning: str = "#FF6D00"
    light_error: str = "#EF5350"

    dark_primary: str = "#E58325"
    dark_accent: str = "#007A99"
    dark_secondary: str = "#973542"
    dark_success: str = "#43A047"
    dark_info: str = "#1976D2"
    dark_warning: str = "#FF6D00"
    dark_error: str = "#EF5350"


class AppStartupInfo(_MarvinModel): ...


class AdminAboutInfo(AppInfo):
    versionLatest: str
    api_port: int
    api_docs: bool
    db_type: str
    db_url: str | None = None
    build_id: str


class CheckAppConfig(_MarvinModel):
    email_ready: bool
    ldap_ready: bool
    oidc_ready: bool
    enable_openai: bool
    base_url_set: bool
    is_up_to_date: bool
