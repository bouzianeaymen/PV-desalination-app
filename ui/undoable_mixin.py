# ui/undoable_mixin.py
"""Undoable Mixin for Pages - Provides common undo/redo functionality"""

import customtkinter
from .undo_manager import UndoManager, ValueChangeCommand, SelectionCommand
from .theme_config import THEME


class UndoablePageMixin:
    """
    Mixin class that provides undo/redo capabilities to pages.
    
    Usage:
        class MyPage(UndoablePageMixin, CTkFrame):
            def __init__(self, parent, app):
                super().__init__(parent, fg_color=THEME.bg.main)
                self._init_undo_system()
                ...
    """
    
    def _init_undo_system(self):
        """Initialize the undo system - call this in __init__ after super().__init__()"""
        self.undo_manager = UndoManager(max_history=100)
    
    def _bind_undo_shortcuts(self, widget=None):
        """Bind Ctrl+Z and Ctrl+Y shortcuts for undo/redo."""
        target = widget if widget else self
        target.bind("<Control-z>", lambda e: self._on_undo())
        target.bind("<Control-y>", lambda e: self._on_redo())
    
    def _on_undo(self):
        """Handle undo action"""
        description = self.undo_manager.undo()
        if description:
            self._update_undo_buttons()
        return "break"
    
    def _on_redo(self):
        """Handle redo action"""
        description = self.undo_manager.redo()
        if description:
            self._update_undo_buttons()
        return "break"
    
    def _update_undo_buttons(self):
        """Update undo/redo button states"""
        if hasattr(self, 'undo_btn') and hasattr(self, 'redo_btn'):
            if self.undo_manager.can_undo():
                self.undo_btn.configure(state="normal", fg_color=THEME.primary.blue)
            else:
                self.undo_btn.configure(state="disabled", fg_color=THEME.bg.disabled)
            
            if self.undo_manager.can_redo():
                self.redo_btn.configure(state="normal", fg_color=THEME.primary.blue)
            else:
                self.redo_btn.configure(state="disabled", fg_color=THEME.bg.disabled)
    
    def _create_undo_buttons(self, parent, side="right"):
        """Create undo/redo buttons with keyboard hint."""
        btn_frame = customtkinter.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(side=side)

        # Keyboard hint
        customtkinter.CTkLabel(
            btn_frame, text="Ctrl+Z / Y",
            font=("Segoe UI", 10), text_color=THEME.text.muted,
        ).pack(side="left", padx=(0, 8))
        
        self.undo_btn = customtkinter.CTkButton(
            btn_frame, text="↩ Undo", width=72, height=30,
            font=("Segoe UI", 11), corner_radius=8,
            fg_color=THEME.bg.disabled, text_color=THEME.text.muted,
            hover_color=THEME.bg.hover, state="disabled",
            command=self._on_undo,
        )
        self.undo_btn.pack(side="left", padx=2)
        
        self.redo_btn = customtkinter.CTkButton(
            btn_frame, text="Redo ↪", width=72, height=30,
            font=("Segoe UI", 11), corner_radius=8,
            fg_color=THEME.bg.disabled, text_color=THEME.text.muted,
            hover_color=THEME.bg.hover, state="disabled",
            command=self._on_redo,
        )
        self.redo_btn.pack(side="left", padx=2)
        
        return btn_frame
    
    def _create_undo_help_text(self, parent):
        """Create help text showing keyboard shortcuts"""
        help_label = customtkinter.CTkLabel(
            parent, text="Ctrl+Z: Undo  |  Ctrl+Y: Redo",
            font=("Segoe UI", 10), text_color=THEME.text.muted,
        )
        help_label.pack(side="left" if hasattr(self, 'undo_btn') else "right", padx=5)
        return help_label
    
    def setup_entry_undo(self, entry_widget, field_name, on_change=None):
        """Setup automatic undo tracking for an entry widget."""
        old_value = {"val": ""}
        
        def on_focus_in(event):
            old_value["val"] = entry_widget.get()
            # Visual focus state
            entry_widget.configure(border_color=THEME.primary.blue, border_width=2)
        
        def on_focus_out(event):
            # Visual unfocus state
            entry_widget.configure(border_color=THEME.border.light, border_width=1)
            new_value = entry_widget.get()
            if new_value != old_value["val"]:
                def setter(value):
                    entry_widget.delete(0, "end")
                    entry_widget.insert(0, str(value))
                
                cmd = ValueChangeCommand(
                    widget_ref=entry_widget,
                    old_value=old_value["val"],
                    new_value=new_value,
                    setter_callback=setter,
                    name=field_name
                )
                self.undo_manager.execute(cmd)
                self._update_undo_buttons()
                
                if on_change:
                    on_change(new_value)
        
        entry_widget.bind("<FocusIn>", on_focus_in)
        entry_widget.bind("<FocusOut>", on_focus_out)
        entry_widget.bind("<Return>", on_focus_out)
    
    def setup_combobox_undo(self, combobox_widget, field_name, on_change=None):
        """Setup automatic undo tracking for a combobox widget."""
        old_value = {"val": combobox_widget.get()}
        
        def on_change_wrapper(choice):
            nonlocal old_value
            new_value = choice
            if new_value != old_value["val"]:
                def setter(value):
                    combobox_widget.set(value)
                
                cmd = SelectionCommand(
                    widget_ref=combobox_widget,
                    old_selection=old_value["val"],
                    new_selection=new_value,
                    setter_callback=setter,
                    name=field_name
                )
                self.undo_manager.execute(cmd)
                self._update_undo_buttons()
                
                if on_change:
                    on_change(new_value)
            
            old_value["val"] = new_value
        
        original_command = combobox_widget.cget("command")
        def wrapped_command(choice):
            on_change_wrapper(choice)
            if original_command:
                original_command(choice)
        
        combobox_widget.configure(command=wrapped_command)
    
    def setup_checkbox_undo(self, checkbox_widget, field_name, on_change=None):
        """Setup automatic undo tracking for a checkbox widget."""
        old_value = {"val": checkbox_widget.get()}
        
        def on_toggle():
            new_value = checkbox_widget.get()
            if new_value != old_value["val"]:
                def setter(value):
                    if value:
                        checkbox_widget.select()
                    else:
                        checkbox_widget.deselect()
                
                from .undo_manager import ToggleCommand
                cmd = ToggleCommand(
                    widget_ref=checkbox_widget,
                    old_state=old_value["val"],
                    new_state=new_value,
                    setter_callback=setter,
                    name=field_name
                )
                self.undo_manager.execute(cmd)
                self._update_undo_buttons()
                
                if on_change:
                    on_change(new_value)
            
            old_value["val"] = new_value
        
        original_command = checkbox_widget.cget("command")
        def wrapped_command():
            on_toggle()
            if original_command:
                original_command()
        
        checkbox_widget.configure(command=wrapped_command)
