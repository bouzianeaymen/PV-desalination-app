# ui/source/constants.py
# Constants for Source Page - Extracted from original source_page.py

# ============================================
# THEME IMPORTS
# ============================================

# Import centralized theme colors
from ui.theme_config import (
    THEME,
    PRIMARY_BLUE,
    PRIMARY_HOVER,
    PRIMARY_LIGHT,
    PRIMARY_DARK,
    BG_MAIN,
    BG_CARD,
    BG_SIDEBAR,
    BG_ELEVATED,
    BG_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    TEXT_PLACEHOLDER,
    SUCCESS_GREEN,
    SUCCESS_DARK,
    SUCCESS_LIGHT,
    ERROR_RED,
    ERROR_LIGHT,
    WARNING_ORANGE,
    INFO_BLUE,
    BORDER_LIGHT,
    BORDER_MEDIUM,
    BG_INPUT,
    BG_INPUT_FOCUS,
    BG_DISABLED,
    BG_SELECTED,
    SOURCE_BLUE,
    DESALINATION_GREEN,
    ECONOMICS_ORANGE,
)

# ============================================
# COLOR PALETTE - Now imported from theme_config.py
# ============================================

# All colors are now imported from ui.theme_config (loaded from apple_modern.json)
# This ensures consistent theming across the entire application
# To modify colors, edit: ui/themes/apple_modern.json

# Shadow and Depth - Modern elevation
SHADOW_SMALL = "0 1px 3px rgba(0,0,0,0.08)"
SHADOW_MEDIUM = "0 4px 12px rgba(0,0,0,0.1)"
SHADOW_LARGE = "0 8px 24px rgba(0,0,0,0.12)"
SHADOW_HOVER = "0 6px 16px rgba(0,0,0,0.15)"

# Typography - Single font family (CTk only supports one family per font tuple)
FONT_FAMILY_DISPLAY = "Segoe UI"
FONT_FAMILY_TEXT = "Segoe UI"

# Font Sizes (consistent hierarchy)
FONT_SIZE_H1 = 32  # Page titles
FONT_SIZE_H2 = 24  # Section headers
FONT_SIZE_H3 = 18  # Card titles, subsections
FONT_SIZE_BODY = 14  # Body text, labels
FONT_SIZE_SMALL = 12  # Captions, hints
FONT_SIZE_TINY = 11  # Metadata, timestamps

# Spacing System (8pt grid)
SPACE_XS = 8    # Tight spacing (icon padding, small gaps)
SPACE_SM = 16   # Small spacing (card inner padding)
SPACE_MD = 24   # Medium spacing (section gaps)
SPACE_LG = 32   # Large spacing (page padding)
SPACE_XL = 40   # Extra large (content margins)
SPACE_2XL = 48  # Huge spacing (major sections)

# Border Radius (consistent rounding)
RADIUS_SM = 8   # Small elements (badges, tags)
RADIUS_MD = 12  # Buttons, inputs
RADIUS_LG = 16  # Cards, panels
RADIUS_XL = 20  # Large cards, modals
RADIUS_FULL = 9999  # Pills, circular elements

# Number formatting: space as thousands separator
def fmt_num(n, decimals=None):
    """Format number with space as thousands separator (e.g. 1 234 567 instead of 1,234,567)."""
    try:
        if decimals is None or decimals == 0:
            return f"{int(float(n)):,}".replace(",", " ")
        return f"{float(n):,.{int(decimals)}f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)

# Component Dimensions
BUTTON_HEIGHT_SM = 32
BUTTON_HEIGHT_MD = 40
BUTTON_HEIGHT_LG = 44
INPUT_HEIGHT = 40
CARD_PADDING = 20

# ============================================
# VALIDATION RANGES
# ============================================

# Coordinate ranges
LAT_MIN, LAT_MAX = -90, 90
LON_MIN, LON_MAX = -180, 180

# Year ranges
YEAR_MIN, YEAR_MAX = 1980, 2100

# System parameters
SLOPE_MIN, SLOPE_MAX = 0, 90
AZIMUTH_MIN, AZIMUTH_MAX = -180, 180
LOSS_MIN, LOSS_MAX = 0, 40
POWER_MIN = 0
CAPACITY_MIN = 0

# Altitude
ALT_MIN, ALT_MAX = -9999, 9999

# Wind parameters (from API)
WIND_HEIGHT_MIN, WIND_HEIGHT_MAX = 10, 300  # Hub height in meters
WIND_CAPACITY_MIN = 0  # kW

# ============================================
# DEFAULT VALUES
# ============================================

DEFAULT_DATABASE_PVGIS = "PVGIS-ERA5"
DEFAULT_DATABASE_TMY = "PVGIS-SARAH3"
DEFAULT_DATASET_NINJA = "CM-SAF SARAH (Europe)"
DEFAULT_MOUNTING = "fixed"
DEFAULT_TRACKING = "None"
DEFAULT_PV_TECH = "Crystalline Silicon"
DEFAULT_OPTIMAL_ANGLES = True

# Ninja PV height for wind speed fetch (hub height, m)
DEFAULT_PV_HEIGHT = 10

# Wind defaults (from API)
DEFAULT_WIND_DATASET = "MERRA-2 (global)"
DEFAULT_WIND_HEIGHT = 80  # meters (API default)
DEFAULT_WIND_TURBINE = "Vestas V90 2000"  # API default
DEFAULT_WIND_CAPACITY = 1  # kW (API default)

# ============================================
# API MAPPINGS
# ============================================

# PVGIS Database options
PVGIS_DATABASES = ["PVGIS-ERA5", "PVGIS-SARAH3"]

# TMY Database options
TMY_DATABASES = ["PVGIS-SARAH3", "PVGIS-ERA5"]

# Ninja Dataset options and API mapping
# Matches official Renewables.ninja datasets
NINJA_DATASETS = ["CM-SAF SARAH (Europe)", "MERRA-2 (global)"]
NINJA_DATASET_MAP = {
    "CM-SAF SARAH (Europe)": "sarah",
    "MERRA-2 (global)": "merra2"
}

# Ninja Tracking options and API mapping
NINJA_TRACKING_OPTIONS = ["None", "Single-axis", "Dual-axis"]
NINJA_TRACKING_MAP = {
    "None": 0,
    "Single-axis": 1,
    "Dual-axis": 2
}

# PV Technology options and API mapping
PV_TECH_OPTIONS = ["Crystalline Silicon", "CdTe", "CIS", "High-efficiency module"]
PV_TECH_MAP = {
    "Crystalline Silicon": "crystSi",
    "CdTe": "CdTe",
    "CIS": "CIS",
    "High-efficiency module": "crystSi"
}

# Mounting type options
MOUNTING_OPTIONS = ["fixed", "vertical_axis", "inclined_axis", "two_axis"]

# ============================================
# UI CONFIGURATION
# ============================================

# Corner radii - Modern, refined
CORNER_RADIUS_CARD = 20      # Larger, more modern cards
CORNER_RADIUS_BUTTON = 12    # Rounded but not pill-shaped
CORNER_RADIUS_BUTTON_PILL = 999  # Pill shape for special buttons
CORNER_RADIUS_FRAME = 28     # Larger frames
CORNER_RADIUS_CIRCLE = 20    # Circular elements
CORNER_RADIUS_INPUT = 10     # Input fields
CORNER_RADIUS_BADGE = 8      # Badges and tags

# Sizes - Enhanced spacing and proportions
SIDEBAR_WIDTH = 220          # Matches app.py sidebar
BUTTON_WIDTH_NAV = 110       # Slightly wider nav buttons
BUTTON_HEIGHT_NAV = 38       # Taller buttons for better touch targets
BUTTON_HEIGHT_PRIMARY = 44   # Primary action buttons
ENTRY_WIDTH = 240            # Wider inputs
COMBO_WIDTH = 320            # Wider combos
CARD_PADDING = 24            # Generous card padding
SECTION_SPACING = 32         # Space between sections

# Typography - Enhanced hierarchy
FONT_SIZE_XL = 32            # Extra large titles
FONT_SIZE_LG = 24            # Large headings
FONT_SIZE_MD = 18            # Medium headings
FONT_SIZE_BASE = 15          # Base text (slightly larger)
FONT_SIZE_SM = 13             # Small text
FONT_SIZE_XS = 11             # Extra small

# Spacing - Consistent rhythm
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32
SPACING_XXL = 48

# ============================================
# STEP CONFIGURATION
# ============================================

STEP_TITLES = {
    1: "Import data",
    2: "Energy"
}

STEP_CONTENT_TITLES = {
    1: "Data Source Configuration",
    2: "Energy"
}
