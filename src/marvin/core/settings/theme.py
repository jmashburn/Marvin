from pydantic_settings import BaseSettings, SettingsConfigDict


class Theme(BaseSettings):
    """
    Application theme color settings.
    Complete theming system with background, text, and accent colors.
    """

    # Light theme - Background & Surface
    light_bg: str = "#fafaf9"  # Stone-50 - main background
    light_panel: str = "#ffffff"  # White - cards, panels
    light_panel_secondary: str = "#f5f5f4"  # Stone-100 - secondary surfaces

    # Light theme - Text & Borders
    light_text: str = "#0c0a09"  # Stone-950 - primary text
    light_text_muted: str = "#57534e"  # Stone-600 - secondary text (improved contrast)
    light_border: str = "#e7e5e4"  # Stone-200 - borders, dividers

    # Light theme - Accent Colors
    light_primary: str = "#ea580c"  # Orange-600 - warm, energetic
    light_accent: str = "#0891b2"  # Cyan-600 - cool, professional
    light_secondary: str = "#7c3aed"  # Violet-600 - rich, distinct
    light_success: str = "#16a34a"  # Green-600 - clear success
    light_info: str = "#0284c7"  # Sky-600 - informative
    light_warning: str = "#d97706"  # Amber-600 - attention-grabbing
    light_error: str = "#dc2626"  # Red-600 - clear error

    # Dark theme - Background & Surface
    dark_bg: str = "#0c0a09"  # Stone-950 - main background
    dark_panel: str = "#1c1917"  # Stone-900 - cards, panels
    dark_panel_secondary: str = "#292524"  # Stone-800 - secondary surfaces

    # Dark theme - Text & Borders
    dark_text: str = "#fafaf9"  # Stone-50 - primary text
    dark_text_muted: str = "#a8a29e"  # Stone-400 - secondary text
    dark_border: str = "#292524"  # Stone-800 - borders, dividers

    # Dark theme - Accent Colors
    dark_primary: str = "#f97316"  # Orange-500 - brighter on dark
    dark_accent: str = "#06b6d4"  # Cyan-500 - pops on dark
    dark_secondary: str = "#8b5cf6"  # Violet-500 - vibrant
    dark_success: str = "#22c55e"  # Green-500 - clear on dark
    dark_info: str = "#0ea5e9"  # Sky-500 - visible
    dark_warning: str = "#f59e0b"  # Amber-500 - stands out
    dark_error: str = "#ef4444"  # Red-500 - clear warning

    model_config = SettingsConfigDict(env_prefix="theme_", extra="allow")
