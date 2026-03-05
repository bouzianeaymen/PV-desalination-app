"""
In-App Toast Notification System
Replaces native messagebox popups for a more professional, integrated UI.
"""
import customtkinter
from .theme_config import THEME

class ToastNotification(customtkinter.CTkFrame):
    def __init__(self, parent, message, type="info", duration=3000):
        # We need to place this on the highest level of the parent
        # Drill up to the root window if possible
        self.root = parent
        while getattr(self.root, "master", None) is not None:
            self.root = self.root.master

        # Determine colors based on type
        if type == "error":
            bg_color = THEME.status.error
            icon = "❌"
        elif type == "success":
            bg_color = THEME.status.success
            icon = "✅"
        elif type == "warning":
            bg_color = THEME.status.warning
            icon = "⚠️"
        else:
            bg_color = THEME.primary.blue
            icon = "ℹ️"

        # Shadow-feeling outer frame (optional, using darker border for now)
        super().__init__(
            self.root,
            fg_color=bg_color,
            corner_radius=10,
            border_width=1,
            border_color=THEME.border.subtle if hasattr(THEME.border, "subtle") else THEME.border.light
        )
        
        self.message = message
        self.duration = duration

        # Content
        lbl_icon = customtkinter.CTkLabel(self, text=icon, font=("Segoe UI", 16), text_color="#FFFFFF")
        lbl_icon.pack(side="left", padx=(16, 10), pady=12)
        
        lbl_msg = customtkinter.CTkLabel(self, text=self.message, font=("Segoe UI", 14, "bold"), text_color="#FFFFFF")
        lbl_msg.pack(side="left", padx=(0, 20), pady=12)
        
        # Bind click to dismiss
        self.bind("<Button-1>", lambda e: self._destroy())
        lbl_icon.bind("<Button-1>", lambda e: self._destroy())
        lbl_msg.bind("<Button-1>", lambda e: self._destroy())

        # Place at top right
        self.place(relx=1.0, rely=0.0, anchor="ne", x=-30, y=30)
        
        # Lift above everything
        self.lift()
        
        # Schedule destruction
        self.root.after(self.duration, self._destroy)

    def _destroy(self):
        try:
            self.destroy()
        except:
            pass

def show_toast(parent, message, type="info", duration=3000):
    """
    Shows a temporary toast notification.
    Args:
        parent: Widget to anchor the toast to (usually self or app).
        message: Text to display.
        type: "info", "success", "error", or "warning".
        duration: Time in ms before it disappears.
    """
    ToastNotification(parent, message, type=type, duration=duration)
