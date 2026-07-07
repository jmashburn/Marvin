from pydantic_settings import BaseSettings, SettingsConfigDict


class Theme(BaseSettings):
    """
    Application theme color settings.
    Modern color palette with better contrast and accessibility.
    """
    # Light theme - Warm orange primary with cool cyan accent
    light_primary: str = "#ea580c"      # Orange-600 - warm, energetic
    light_accent: str = "#0891b2"       # Cyan-600 - cool, professional
    light_secondary: str = "#7c3aed"    # Violet-600 - rich, distinct
    light_success: str = "#16a34a"      # Green-600 - clear success
    light_info: str = "#0284c7"         # Sky-600 - informative
    light_warning: str = "#d97706"      # Amber-600 - attention-grabbing
    light_error: str = "#dc2626"        # Red-600 - clear error

    # Dark theme - Brighter variations for dark backgrounds
    dark_primary: str = "#f97316"       # Orange-500 - brighter on dark
    dark_accent: str = "#06b6d4"        # Cyan-500 - pops on dark
    dark_secondary: str = "#8b5cf6"     # Violet-500 - vibrant
    dark_success: str = "#22c55e"       # Green-500 - clear on dark
    dark_info: str = "#0ea5e9"          # Sky-500 - visible
    dark_warning: str = "#f59e0b"       # Amber-500 - stands out
    dark_error: str = "#ef4444"         # Red-500 - clear warning

    model_config = SettingsConfigDict(env_prefix="theme_", extra="allow")
