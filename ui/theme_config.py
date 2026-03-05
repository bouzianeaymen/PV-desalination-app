"""
Theme Configuration Loader
Loads colors from JSON theme files and provides structured access
"""

import json
import os
from typing import Any, Dict


class ThemeDict:
    """Nested dictionary with dot notation access"""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ThemeDict(value))
            else:
                setattr(self, key, value)
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get value by dot-separated path, e.g., 'primary.blue'"""
        keys = path.split('.')
        value = self._data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
    
    def __repr__(self) -> str:
        return f"ThemeDict({self._data})"


class Theme:
    """Main theme loader and accessor"""
    
    def __init__(self, theme_file: str = "apple_modern.json", mode: str = "light"):
        """
        Load theme from JSON file
        
        Args:
            theme_file: Name of theme file in ui/themes/ directory
            mode: 'light' or 'dark' (default: 'light')
        """
        self.mode = mode
        self.theme_file = theme_file
        
        # Locate theme file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        themes_dir = os.path.join(current_dir, 'themes')
        theme_path = os.path.join(themes_dir, theme_file)
        
        if not os.path.exists(theme_path):
            raise FileNotFoundError(f"Theme file not found: {theme_path}")
        
        # Load JSON
        with open(theme_path, 'r', encoding='utf-8') as f:
            theme_data = json.load(f)
        
        # Extract metadata
        self.name = theme_data.get('name', 'Unknown')
        self.version = theme_data.get('version', '1.0')
        self.description = theme_data.get('description', '')
        
        # Load mode-specific colors
        if mode not in theme_data.get('modes', {}):
            raise ValueError(f"Theme mode '{mode}' not found in {theme_file}")
        
        mode_colors = theme_data['modes'][mode]
        
        # Create nested theme accessors
        self.primary = ThemeDict(mode_colors.get('primary', {}))
        self.background = ThemeDict(mode_colors.get('background', {}))
        self.bg = self.background  # Shorthand alias
        self.text = ThemeDict(mode_colors.get('text', {}))
        self.status = ThemeDict(mode_colors.get('status', {}))
        self.border = ThemeDict(mode_colors.get('border', {}))
        self.module = ThemeDict(mode_colors.get('module', {}))
        self.semantic = ThemeDict(mode_colors.get('semantic', {}))
        
        # Store full mode data for direct access
        self._colors = mode_colors
    
    def get_color(self, path: str, default: str = "#000000") -> str:
        """
        Get color by dot-separated path
        
        Args:
            path: Path like 'primary.blue' or 'text.secondary'
            default: Fallback color if path not found
            
        Returns:
            Hex color string
        """
        parts = path.split('.', 1)
        if len(parts) != 2:
            return default
        
        category, key = parts
        if hasattr(self, category):
            return getattr(self, category).get(key, default)
        return default
    
    def switch_mode(self, mode: str):
        """Switch between light and dark modes"""
        if mode not in ['light', 'dark']:
            raise ValueError(f"Invalid mode: {mode}. Use 'light' or 'dark'")
        
        # Reload with new mode
        self.__init__(self.theme_file, mode)


# Global theme instance (light mode by default)
THEME = Theme(mode='light')


# Export commonly used colors as module-level constants for backward compatibility
# These can be imported directly: from ui.theme_config import PRIMARY_BLUE
PRIMARY_BLUE = THEME.primary.blue
PRIMARY_HOVER = THEME.primary.blue_hover
PRIMARY_LIGHT = THEME.primary.blue_light
PRIMARY_DARK = THEME.primary.blue_dark

BG_MAIN = THEME.bg.main
BG_CARD = THEME.bg.card
BG_SIDEBAR = THEME.bg.sidebar
BG_ELEVATED = THEME.bg.elevated
BG_HOVER = THEME.bg.hover

TEXT_PRIMARY = THEME.text.primary
TEXT_SECONDARY = THEME.text.secondary
TEXT_MUTED = THEME.text.muted
TEXT_PLACEHOLDER = THEME.text.placeholder

SUCCESS_GREEN = THEME.status.success
SUCCESS_DARK = THEME.status.success_dark
SUCCESS_LIGHT = THEME.status.success_light
ERROR_RED = THEME.status.error
ERROR_LIGHT = THEME.status.error_light
WARNING_ORANGE = THEME.status.warning
INFO_BLUE = THEME.status.info

BORDER_LIGHT = THEME.border.light
BORDER_MEDIUM = THEME.border.medium

BG_INPUT = THEME.bg.input
BG_INPUT_FOCUS = THEME.bg.input_focus
BG_DISABLED = THEME.bg.disabled
BG_SELECTED = THEME.bg.selected

SOURCE_BLUE = THEME.module.source
DESALINATION_GREEN = THEME.module.desalination
ECONOMICS_ORANGE = THEME.module.economics


def get_theme_color(path: str, default: str = "#000000") -> str:
    """
    Helper function to get theme colors by path
    
    Usage:
        color = get_theme_color('primary.blue')
        bg = get_theme_color('background.card')
    """
    return THEME.get_color(path, default)
