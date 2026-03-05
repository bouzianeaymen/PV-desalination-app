"""
Modern Component Wrappers
Themed versions of CustomTkinter widgets with consistent styling
All wrappers preserve original callbacks and parameters
"""

import customtkinter
from .theme_config import THEME


def ModernButton(
    parent,
    text: str,
    command=None,
    width: int = None,
    height: int = 44,
    style: str = "primary",
    **kwargs
):
    """
    Modern themed button with consistent styling
    
    Args:
        parent: Parent widget
        text: Button text
        command: Callback function (preserved)
        width: Button width (optional)
        height: Button height (default: 44)
        style: 'primary', 'secondary', 'success', 'danger', 'ghost'
        **kwargs: Additional CTkButton parameters (override defaults)
    
    Returns:
        CTkButton instance
    """
    # Define style presets
    styles = {
        "primary": {
            "fg_color": THEME.primary.blue,
            "hover_color": THEME.primary.blue_hover,
            "text_color": "#FFFFFF",
            "border_width": 0,
        },
        "secondary": {
            "fg_color": THEME.bg.input,
            "hover_color": THEME.bg.hover,
            "text_color": THEME.text.secondary,
            "border_width": 1,
            "border_color": THEME.border.light,
        },
        "success": {
            "fg_color": THEME.status.success,
            "hover_color": THEME.status.success_dark,
            "text_color": "#FFFFFF",
            "border_width": 0,
        },
        "danger": {
            "fg_color": THEME.status.error,
            "hover_color": "#E02020",
            "text_color": "#FFFFFF",
            "border_width": 0,
        },
        "ghost": {
            "fg_color": "transparent",
            "hover_color": THEME.bg.hover,
            "text_color": THEME.text.primary,
            "border_width": 0,
        },
    }
    
    # Get style config
    style_config = styles.get(style, styles["primary"])
    
    # Merge with user overrides (kwargs always win)
    config = {
        "corner_radius": 12,
        "font": ("SF Pro Text", 15),
        **style_config,
        **kwargs,  # User params override everything
    }
    
    return customtkinter.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        **config
    )


def ModernEntry(
    parent,
    placeholder_text: str = "",
    width: int = 240,
    **kwargs
):
    """
    Modern themed entry field with focus states
    
    Args:
        parent: Parent widget
        placeholder_text: Placeholder text
        width: Entry width (default: 240)
        **kwargs: Additional CTkEntry parameters
    
    Returns:
        CTkEntry instance with focus state bindings
    """
    config = {
        "corner_radius": 10,
        "border_width": 1,
        "border_color": THEME.border.light,
        "fg_color": THEME.bg.input,
        "text_color": THEME.text.primary,
        "placeholder_text_color": THEME.text.placeholder,
        "font": ("Segoe UI", 14),
        "height": 40,
        **kwargs,  # User overrides
    }
    
    entry = customtkinter.CTkEntry(
        parent,
        placeholder_text=placeholder_text,
        width=width,
        **config
    )
    
    # Add focus state animations
    def on_focus_in(event):
        entry.configure(
            fg_color=THEME.bg.input_focus,
            border_color=THEME.primary.blue,
            border_width=2
        )
    
    def on_focus_out(event):
        entry.configure(
            fg_color=THEME.bg.input,
            border_color=THEME.border.light,
            border_width=1
        )
    
    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    
    return entry


def ModernComboBox(
    parent,
    values: list,
    command=None,
    width: int = 320,
    **kwargs
):
    """
    Modern themed combobox
    
    Args:
        parent: Parent widget
        values: List of options
        command: Callback function (preserved)
        width: Combobox width (default: 320)
        **kwargs: Additional CTkComboBox parameters
    
    Returns:
        CTkComboBox instance
    """
    config = {
        "corner_radius": 10,
        "border_width": 1,
        "border_color": THEME.border.light,
        "fg_color": THEME.bg.input,
        "button_color": THEME.primary.blue,
        "button_hover_color": THEME.primary.blue_hover,
        "dropdown_fg_color": THEME.bg.card,
        "dropdown_hover_color": THEME.bg.selected,
        "text_color": THEME.text.primary,
        "font": ("SF Pro Text", 14),
        **kwargs,
    }
    
    return customtkinter.CTkComboBox(
        parent,
        values=values,
        command=command,
        width=width,
        **config
    )


def ModernCheckBox(
    parent,
    text: str,
    variable=None,
    command=None,
    **kwargs
):
    """
    Modern themed checkbox
    
    Args:
        parent: Parent widget
        text: Checkbox label
        variable: tkinter Variable (preserved)
        command: Callback function (preserved)
        **kwargs: Additional CTkCheckBox parameters
    
    Returns:
        CTkCheckBox instance
    """
    config = {
        "corner_radius": 6,
        "border_width": 2,
        "fg_color": THEME.primary.blue,
        "hover_color": THEME.primary.blue_hover,
        "border_color": THEME.border.medium,
        "text_color": THEME.text.primary,
        "font": ("SF Pro Text", 12),
        **kwargs,
    }
    
    return customtkinter.CTkCheckBox(
        parent,
        text=text,
        variable=variable,
        command=command,
        **config
    )


def ModernLabel(
    parent,
    text: str,
    style: str = "body",
    **kwargs
):
    """
    Modern themed label with typography presets
    
    Args:
        parent: Parent widget
        text: Label text
        style: 'title', 'heading', 'subheading', 'body', 'caption', 'muted'
        **kwargs: Additional CTkLabel parameters
    
    Returns:
        CTkLabel instance
    """
    # Typography presets
    typography = {
        "title": {
            "font": ("SF Pro Display", 28, "bold"),
            "text_color": THEME.text.primary,
        },
        "heading": {
            "font": ("SF Pro Display", 20, "bold"),
            "text_color": THEME.text.primary,
        },
        "subheading": {
            "font": ("SF Pro Display", 16, "bold"),
            "text_color": THEME.text.primary,
        },
        "body": {
            "font": ("SF Pro Text", 14),
            "text_color": THEME.text.primary,
        },
        "caption": {
            "font": ("SF Pro Text", 12),
            "text_color": THEME.text.secondary,
        },
        "muted": {
            "font": ("SF Pro Text", 12),
            "text_color": THEME.text.muted,
        },
    }
    
    style_config = typography.get(style, typography["body"])
    config = {**style_config, **kwargs}
    
    return customtkinter.CTkLabel(
        parent,
        text=text,
        **config
    )


def ModernFrame(
    parent,
    style: str = "card",
    **kwargs
):
    """
    Modern themed frame with style presets
    
    Args:
        parent: Parent widget
        style: 'card', 'section', 'sidebar', 'transparent'
        **kwargs: Additional CTkFrame parameters
    
    Returns:
        CTkFrame instance
    """
    # Frame style presets
    styles = {
        "card": {
            "fg_color": THEME.bg.card,
            "corner_radius": 20,
            "border_width": 1,
            "border_color": THEME.border.light,
        },
        "section": {
            "fg_color": THEME.bg.card,
            "corner_radius": 16,
            "border_width": 0,
        },
        "sidebar": {
            "fg_color": THEME.bg.sidebar,
            "corner_radius": 20,
            "border_width": 0,
        },
        "transparent": {
            "fg_color": "transparent",
            "corner_radius": 0,
            "border_width": 0,
        },
    }
    
    style_config = styles.get(style, styles["transparent"])
    config = {**style_config, **kwargs}
    
    return customtkinter.CTkFrame(parent, **config)


def ModernScrollableFrame(
    parent,
    **kwargs
):
    """
    Modern themed scrollable frame with consistent scrollbar styling
    
    Args:
        parent: Parent widget
        **kwargs: Additional CTkScrollableFrame parameters
    
    Returns:
        CTkScrollableFrame instance
    """
    config = {
        "fg_color": "transparent",
        "scrollbar_button_color": THEME.border.gray,
        "scrollbar_button_hover_color": THEME.text.gray_medium,
        "corner_radius": 0,
        **kwargs,
    }
    
    return customtkinter.CTkScrollableFrame(parent, **config)


def ModernRadioButton(
    parent,
    text: str,
    variable=None,
    value=None,
    command=None,
    **kwargs
):
    """
    Modern themed radio button
    
    Args:
        parent: Parent widget
        text: Radio button label
        variable: tkinter Variable (preserved)
        value: Value when selected
        command: Callback function (preserved)
        **kwargs: Additional CTkRadioButton parameters
    
    Returns:
        CTkRadioButton instance
    """
    config = {
        "fg_color": THEME.primary.blue,
        "hover_color": THEME.primary.blue_hover,
        "border_color": THEME.border.medium,
        "text_color": THEME.text.primary,
        "font": ("SF Pro Text", 12),
        **kwargs,
    }
    
    return customtkinter.CTkRadioButton(
        parent,
        text=text,
        variable=variable,
        value=value,
        command=command,
        **config
    )


# Utility functions for creating common patterns

def create_labeled_entry(parent, label_text: str, placeholder: str = "", unit: str = "", **entry_kwargs):
    """
    Create a label + entry pair (common pattern)
    
    Args:
        parent: Parent frame (should use grid layout)
        label_text: Label text
        placeholder: Entry placeholder
        unit: Unit suffix (e.g., "°C", "kWp")
        **entry_kwargs: Additional entry parameters
    
    Returns:
        tuple: (label_widget, entry_widget)
    """
    label_with_unit = f"{label_text} ({unit}):" if unit else f"{label_text}:"
    
    label = ModernLabel(parent, text=label_with_unit, style="caption")
    entry = ModernEntry(parent, placeholder_text=placeholder, **entry_kwargs)
    
    return label, entry


def create_section_header(parent, title: str, subtitle: str = None):
    """
    Create a section header with optional subtitle
    
    Args:
        parent: Parent widget
        title: Section title
        subtitle: Optional subtitle text
    
    Returns:
        Frame containing the header
    """
    header_frame = ModernFrame(parent, style="transparent")
    
    title_label = ModernLabel(header_frame, text=title, style="heading")
    title_label.pack(anchor="w")
    
    if subtitle:
        subtitle_label = ModernLabel(header_frame, text=subtitle, style="caption")
        subtitle_label.pack(anchor="w", pady=(4, 0))
    
    return header_frame


def create_button_group(parent, buttons: list, align: str = "right"):
    """
    Create a group of buttons with consistent spacing
    
    Args:
        parent: Parent widget
        buttons: List of dicts with button config: [{"text": "Save", "command": fn, "style": "primary"}, ...]
        align: 'left', 'right', or 'center'
    
    Returns:
        Frame containing the buttons
    """
    button_frame = ModernFrame(parent, style="transparent")
    
    for btn_config in buttons:
        text = btn_config.pop("text")
        command = btn_config.pop("command", None)
        style = btn_config.pop("style", "secondary")
        
        btn = ModernButton(button_frame, text=text, command=command, style=style, **btn_config)
        
        if align == "left":
            btn.pack(side="left", padx=(0, 12))
        elif align == "right":
            btn.pack(side="right", padx=(12, 0))
        else:  # center
            btn.pack(side="left", padx=6)
    
    return button_frame
