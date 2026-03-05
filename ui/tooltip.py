"""
Custom Tooltip Component
Shows a floating text box when hovering over a widget.
"""
import customtkinter
from .theme_config import THEME

class ToolTip:
    def __init__(self, widget, text, delay=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.schedule, add="+")
        self.widget.bind("<Leave>", self.hide, add="+")
        self.widget.bind("<ButtonPress>", self.hide, add="+")

    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def show(self, event=None):
        self.unschedule()
        if self.tooltip_window:
            return
            
        # Determine position
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        # Create toplevel
        self.tooltip_window = customtkinter.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)
        
        # Transparent background trick (depends on OS)
        if self.tooltip_window._get_window_bindings() and hasattr(self.tooltip_window, "wm_attributes"):
            try:
                self.tooltip_window.wm_attributes("-transparentcolor", "white")
                self.tooltip_window.configure(fg_color="white")
            except:
                pass

        # Frame for styling
        frame = customtkinter.CTkFrame(
            self.tooltip_window, 
            fg_color=THEME.bg.card, 
            corner_radius=6,
            border_width=1,
            border_color=THEME.border.light
        )
        frame.pack(fill="both", expand=True)

        label = customtkinter.CTkLabel(
            frame, 
            text=self.text, 
            justify="left",
            font=("Segoe UI", 12),
            text_color=THEME.text.secondary,
            wraplength=250
        )
        label.pack(padx=10, pady=8)

    def hide(self, event=None):
        self.unschedule()
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def add_tooltip(widget, text, delay=300):
    """Convenience function to add a tooltip to a widget"""
    return ToolTip(widget, text, delay)
