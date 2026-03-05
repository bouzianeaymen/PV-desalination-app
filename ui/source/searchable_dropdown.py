# ui/source/searchable_dropdown.py
# Searchable dropdown: entry + scrollable list with type-to-filter and scrollbar.
# Debounced typing and capped display to avoid lag with large lists.
# 2026 macOS-style: editable entry filters inline, clean minimal popup.

import customtkinter
from typing import List, Callable, Optional, Any

# Default max options to render at once (avoids lag); show "Type more to narrow" if more matches
MAX_DISPLAY_OPTIONS = 100
DEBOUNCE_MS = 250
# When entry shows one of these, treat as empty query so full list is shown
SENTINEL_VALUES = ("— Select —", "— Select —".lower())
DROPDOWN_MIN_HEIGHT = 100
DROPDOWN_MAX_HEIGHT = 280
ITEM_HEIGHT = 36
LIST_PADX, LIST_PADY = 4, 2
CORNER_RADIUS = 10

# Modern color palette
_POPUP_BG = ("gray97", "gray16")
_POPUP_BORDER = ("#E0E0E4", "gray30")
_ITEM_HOVER = ("#F0F0F5", "gray25")
_ITEM_SELECTED_BG = ("#E8F0FE", "gray28")
_ITEM_TEXT = ("gray10", "gray90")
_SCROLLBAR_COLOR = ("gray82", "gray38")
_SCROLLBAR_HOVER = ("gray70", "gray32")


class SearchableDropdown(customtkinter.CTkFrame):
    """
    Entry with a dropdown list that shows filtered options as the user types.
    List is scrollable (mouse scroll). Selection sets the entry value and calls command.

    The main entry is always editable — typing filters the dropdown list live.
    Arrow button toggles the dropdown open/closed.
    """

    def __init__(
        self,
        parent,
        values: Optional[List[str]] = None,
        width: int = 220,
        height: int = 36,
        placeholder: str = "— Select —",
        command: Optional[Callable[[str], None]] = None,
        fg_color: Optional[str] = None,
        empty_message: Optional[str] = None,
        combo_style: bool = False,
        arrow_fg_color: Optional[str] = None,
        arrow_text_color: Optional[str] = None,
        arrow_hover_color: Optional[str] = None,
        max_display_options: Optional[int] = None,
        custom_filter: Optional[Callable[[str], List[str]]] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._values = list(values or [])
        self._max_display_options = max_display_options if max_display_options is not None else MAX_DISPLAY_OPTIONS
        self._custom_filter = custom_filter
        self._command = command
        self._placeholder = placeholder
        self._empty_message = empty_message or ""
        self._combo_style = combo_style  # kept for API compat but entry is always editable now
        self._dropdown_win: Optional[Any] = None
        self._scroll_frame: Optional[Any] = None
        self._after_id: Optional[str] = None
        self._show_after_id: Optional[str] = None
        self._just_selected = False
        self._current_display_options: List[str] = []
        self._keyboard_highlight_index: int = 0
        self._overlay_win: Optional[Any] = None
        self._browse_mode: bool = False  # True when opened by arrow/click → show full list

        self.entry = customtkinter.CTkEntry(
            self,
            width=width,
            height=height,
            placeholder_text=placeholder,
            font=("Segoe UI", 13),
            fg_color=fg_color,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=("#D1D5DB", "gray35"),
        )
        self.entry.pack(side="left", fill="x", expand=True)
        # Always editable — typing filters the list
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Button-1>", self._on_entry_click)

        # Modern arrow button: subtle chevron
        btn_fg = arrow_fg_color if arrow_fg_color is not None else ("#F3F4F6", "gray25")
        btn_text = arrow_text_color if arrow_text_color is not None else ("#6B7280", "gray70")
        btn_hover = arrow_hover_color if arrow_hover_color is not None else ("#E5E7EB", "gray30")
        self._btn = customtkinter.CTkButton(
            self,
            text="▾",
            width=36,
            height=height,
            font=("Segoe UI", 12),
            fg_color=btn_fg,
            text_color=btn_text,
            corner_radius=CORNER_RADIUS,
            hover_color=btn_hover,
            border_width=1,
            border_color=("#D1D5DB", "gray35"),
            command=self._toggle_dropdown,
        )
        self._btn.pack(side="right", padx=(4, 0))

    def get(self) -> str:
        return (self.entry.get() or "").strip()

    def set(self, value: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, value or "")

    def set_values(self, values: List[str]):
        self._values = list(values or [])
        self._hide_dropdown()

    def set_empty_message(self, message: Optional[str] = None):
        """Update the message shown when the list has no real options."""
        self._empty_message = (message or "").strip()

    def _is_empty_query(self, raw: str) -> bool:
        if not raw:
            return True
        r = raw.lower()
        if self._placeholder and r == self._placeholder.lower():
            return True
        if r in SENTINEL_VALUES or raw == "— Select —":
            return True
        return False

    def _filter(self, query: str) -> List[str]:
        raw = (query or "").strip()
        if self._custom_filter is not None:
            return self._custom_filter(raw)
        if self._is_empty_query(raw):
            return self._values[:]
        q = raw.lower()
        return [v for v in self._values if q in v.lower()]

    def _filter_capped(self, query: str) -> tuple:
        """Return (options_to_show, total_match_count)."""
        matched = self._filter(query)
        total = len(matched)
        display = matched[: self._max_display_options]
        return (display, total)

    def _get_filter_query(self) -> str:
        """Filter query from main entry."""
        return (self.entry.get() or "").strip()

    def _get_effective_filter_query(self) -> str:
        """Filter query; empty in browse mode (opened by arrow/click) to show full list."""
        if self._browse_mode:
            return ""
        return self._get_filter_query()

    def _delayed_show_dropdown(self):
        self._show_after_id = None
        try:
            root = self.winfo_toplevel()
            if root and root.winfo_exists():
                focus_w = getattr(root, "focus_get", lambda: None)()
                if focus_w is not None and focus_w != self.entry:
                    return
        except Exception:
            pass
        self._browse_mode = True
        self._show_dropdown()

    def _on_entry_click(self, event=None):
        """Open dropdown on click."""
        if self._just_selected:
            return
        if self._show_after_id:
            self.after_cancel(self._show_after_id)
        self._show_after_id = self.after(50, self._delayed_show_dropdown)

    def _on_overlay_click(self, event=None):
        """Click outside dropdown: close."""
        self.after(0, self._hide_dropdown)

    def _on_escape_key(self, event=None):
        """Escape: close dropdown without changing value."""
        try:
            if self.winfo_exists() and self._dropdown_win and self._dropdown_win.winfo_exists() and self._dropdown_win.winfo_viewable():
                self._hide_dropdown()
                return "break"
        except Exception:
            pass

    def _create_overlay(self):
        """Four strips around combo+dropdown so click-outside hits overlay."""
        self._destroy_overlay()
        root = self.winfo_toplevel()
        if not root or not root.winfo_exists():
            return
        try:
            root.update_idletasks()
            rw, rh = root.winfo_width(), root.winfo_height()
            rx, ry = root.winfo_rootx(), root.winfo_rooty()
            cx1, cy1 = self.winfo_rootx(), self.winfo_rooty()
            cx2, cy2 = cx1 + self.winfo_width(), cy1 + self.winfo_height()
            dx1, dy1 = rx, ry
            dx2, dy2 = rx + rw, ry + rh
            if self._dropdown_win and self._dropdown_win.winfo_exists():
                dx1 = self._dropdown_win.winfo_rootx()
                dy1 = self._dropdown_win.winfo_rooty()
                dx2 = dx1 + self._dropdown_win.winfo_width()
                dy2 = dy1 + self._dropdown_win.winfo_height()
            bx1 = min(cx1, dx1)
            by1 = min(cy1, dy1)
            bx2 = max(cx2, dx2)
            by2 = max(cy2, dy2)
            strips = []
            if by1 > ry:
                strips.append((rx, ry, rw, by1 - ry))
            if by2 < ry + rh:
                strips.append((rx, by2, rw, (ry + rh) - by2))
            if bx1 > rx:
                strips.append((rx, by1, bx1 - rx, by2 - by1))
            if bx2 < rx + rw:
                strips.append((bx2, by1, (rx + rw) - bx2, by2 - by1))
            self._overlay_win = []
            for (sx, sy, sw, sh) in strips:
                if sw <= 0 or sh <= 0:
                    continue
                win = customtkinter.CTkToplevel(root)
                win.withdraw()
                win.overrideredirect(True)
                win.attributes("-topmost", True)
                win.attributes("-alpha", 0.01)
                win.configure(fg_color=("gray10", "gray10"))
                win.bind("<Button-1>", self._on_overlay_click)
                win.geometry(f"{max(1, int(sw))}x{max(1, int(sh))}+{int(sx)}+{int(sy)}")
                win.deiconify()
                win.lift()
                self._overlay_win.append(win)
        except Exception:
            self._destroy_overlay()

    def _destroy_overlay(self):
        try:
            if self._overlay_win is not None:
                if isinstance(self._overlay_win, list):
                    for w in self._overlay_win:
                        if w and w.winfo_exists():
                            w.destroy()
                elif self._overlay_win.winfo_exists():
                    self._overlay_win.destroy()
        except Exception:
            pass
        self._overlay_win = None

    def _bind_close_handlers(self):
        """Bind overlay + keyboard nav on entry."""
        self._create_overlay()
        if self._dropdown_win and self._dropdown_win.winfo_exists():
            self._dropdown_win.lift()
        self.entry.bind("<Escape>", self._on_escape_key, add="+")
        self.entry.bind("<Down>", self._on_key_down, add="+")
        self.entry.bind("<Up>", self._on_key_up, add="+")
        self.entry.bind("<Return>", self._on_key_return, add="+")

    def _unbind_close_handlers(self):
        """Remove keyboard bindings when dropdown is hidden."""
        try:
            self.entry.unbind("<Escape>")
        except Exception:
            pass
        try:
            self.entry.unbind("<Down>")
        except Exception:
            pass
        try:
            self.entry.unbind("<Up>")
        except Exception:
            pass
        try:
            self.entry.unbind("<Return>")
        except Exception:
            pass

    def _on_key_down(self, event=None):
        """Move highlight down."""
        if not self._current_display_options or not (self._dropdown_win and self._dropdown_win.winfo_viewable()):
            return
        self._keyboard_highlight_index = min(
            len(self._current_display_options) - 1,
            self._keyboard_highlight_index + 1,
        )
        self._refresh_dropdown()
        self._scroll_highlight_into_view()
        return "break"

    def _on_key_up(self, event=None):
        """Move highlight up."""
        if not self._current_display_options or not (self._dropdown_win and self._dropdown_win.winfo_viewable()):
            return
        self._keyboard_highlight_index = max(0, self._keyboard_highlight_index - 1)
        self._refresh_dropdown()
        self._scroll_highlight_into_view()
        return "break"

    def _on_key_return(self, event=None):
        """Select highlighted option and close."""
        if not self._current_display_options or not (self._dropdown_win and self._dropdown_win.winfo_viewable()):
            return
        if 0 <= self._keyboard_highlight_index < len(self._current_display_options):
            value = self._current_display_options[self._keyboard_highlight_index]
            self._select(value)
        return "break"

    def _scroll_highlight_into_view(self):
        """Scroll dropdown so the highlighted item is visible."""
        if not self._scroll_frame or not self._current_display_options:
            return
        try:
            children = self._scroll_frame.winfo_children()
            idx = self._keyboard_highlight_index
            if 0 <= idx < len(children):
                child = children[idx]
                canvas = getattr(self._scroll_frame, "_parent_canvas", None) or getattr(self._scroll_frame, "parent_canvas", None)
                if canvas and hasattr(canvas, "see"):
                    canvas.see(child)
        except Exception:
            pass

    def _on_key(self, event=None):
        self._browse_mode = False
        # Open dropdown on typing if not already open
        if self._dropdown_win is None or not self._dropdown_win.winfo_exists() or not self._dropdown_win.winfo_viewable():
            if not self._just_selected:
                self._show_dropdown()
                return
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(DEBOUNCE_MS, self._debounced_refresh)

    def _debounced_refresh(self):
        self._after_id = None
        self._refresh_dropdown()

    def _toggle_dropdown(self):
        if self._dropdown_win and self._dropdown_win.winfo_viewable():
            self._hide_dropdown()
        else:
            self._browse_mode = True
            self._show_dropdown()

    def _show_dropdown(self):
        if self._just_selected:
            return
        if self._dropdown_win is not None and self._dropdown_win.winfo_exists():
            self._refresh_dropdown()
            try:
                self._dropdown_win.deiconify()
                self._dropdown_win.lift()
                self._bind_close_handlers()
            except Exception:
                self._create_dropdown_window()
            return
        self._create_dropdown_window()

    def _destroy_old_dropdown(self, win: Any):
        """Defer destroying the previous dropdown."""
        try:
            if win and win.winfo_exists():
                win.destroy()
        except Exception:
            pass

    def _create_dropdown_window(self):
        old_win = self._dropdown_win
        if old_win and old_win.winfo_exists():
            self.after(250, lambda: self._destroy_old_dropdown(old_win))
        self._dropdown_win = None
        root = self.winfo_toplevel()
        if not root or not root.winfo_exists():
            return
        self._dropdown_win = customtkinter.CTkToplevel(root)
        self._dropdown_win.withdraw()
        self._dropdown_win.overrideredirect(True)
        self._dropdown_win.attributes("-topmost", True)
        self._dropdown_win.configure(
            fg_color=_POPUP_BG,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=_POPUP_BORDER,
        )
        self._dropdown_win.withdraw()

        list_outer = customtkinter.CTkFrame(
            self._dropdown_win, fg_color="transparent",
            corner_radius=CORNER_RADIUS,
        )
        list_outer.pack(fill="both", expand=True, padx=4, pady=4)

        # No separate filter entry — main entry does the filtering
        query = self._get_effective_filter_query()
        display, _ = self._filter_capped(query)
        drop_w = max(self.entry.winfo_reqwidth() + 24, 200)
        list_h = min(DROPDOWN_MAX_HEIGHT, max(DROPDOWN_MIN_HEIGHT, len(display) * (ITEM_HEIGHT + LIST_PADY * 2) + 20))
        self._scroll_frame = customtkinter.CTkScrollableFrame(
            list_outer,
            height=list_h,
            width=drop_w,
            fg_color="transparent",
            scrollbar_button_color=_SCROLLBAR_COLOR,
            scrollbar_button_hover_color=_SCROLLBAR_HOVER,
        )
        self._scroll_frame.pack(fill="both", expand=True)
        display, total = self._filter_capped(self._get_effective_filter_query())
        current = self.get()
        self._keyboard_highlight_index = display.index(current) if current in display else 0
        self._populate_list(display, total)
        self._position_and_show(display)
        self._bind_close_handlers()

    def _position_and_show(self, display_options: List[str]):
        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        w = max(self.entry.winfo_reqwidth() + 48, 220)
        n = len(display_options)
        content_h = n * (ITEM_HEIGHT + LIST_PADY * 2) + 20
        if self._empty_message and n == 1 and (display_options[0] == "— Select —" or display_options[0] == self._placeholder):
            content_h = DROPDOWN_MIN_HEIGHT - 16
        list_h = min(DROPDOWN_MAX_HEIGHT, max(DROPDOWN_MIN_HEIGHT, content_h))
        self._dropdown_win.geometry(f"{w}x{list_h}+{x}+{y}")
        self._dropdown_win.deiconify()
        self._dropdown_win.lift()

    def _refresh_dropdown(self):
        if self._dropdown_win is None or not self._dropdown_win.winfo_exists():
            return
        query = self._get_effective_filter_query()
        display, total = self._filter_capped(query)
        if display:
            self._keyboard_highlight_index = min(max(0, self._keyboard_highlight_index), len(display) - 1)
        else:
            self._keyboard_highlight_index = 0
        self._populate_list(display, total)
        if self._scroll_frame:
            n = len(display)
            content_h = n * (ITEM_HEIGHT + LIST_PADY * 2) + 20
            if self._empty_message and n == 1 and (display[0] == "— Select —" or display[0] == self._placeholder):
                content_h = DROPDOWN_MIN_HEIGHT - 16
            h = min(DROPDOWN_MAX_HEIGHT, max(DROPDOWN_MIN_HEIGHT, content_h))
            self._scroll_frame.configure(height=h)
            self._position_and_show(display)

    def _populate_list(self, options: List[str], total_matches: Optional[int] = None):
        if self._scroll_frame is None:
            return
        self._current_display_options = list(options) if options else []
        for w in self._scroll_frame.winfo_children():
            w.destroy()
        current = self.get()
        # Empty state
        if self._empty_message and len(options) == 1 and (options[0] == "— Select —" or options[0] == self._placeholder):
            self._current_display_options = []
            lbl = customtkinter.CTkLabel(
                self._scroll_frame,
                text=self._empty_message,
                font=("Segoe UI", 12),
                text_color=("gray50", "gray55"),
                wraplength=240,
                justify="left",
            )
            lbl.pack(fill="x", padx=12, pady=20)
            return
        # No matches
        if not options:
            lbl = customtkinter.CTkLabel(
                self._scroll_frame,
                text="No matching results",
                font=("Segoe UI", 12),
                text_color=("gray50", "gray55"),
            )
            lbl.pack(fill="x", padx=12, pady=20)
            return
        hi = self._keyboard_highlight_index if 0 <= self._keyboard_highlight_index < len(options) else -1
        for i, val in enumerate(options):
            is_selected = (val == current)
            is_highlighted = (i == hi)
            if is_selected:
                item_bg = _ITEM_SELECTED_BG
            elif is_highlighted:
                item_bg = _ITEM_HOVER
            else:
                item_bg = "transparent"
            # Use CTkLabel instead of CTkButton for lighter rendering (less lag)
            lbl = customtkinter.CTkLabel(
                self._scroll_frame,
                text=val,
                anchor="w",
                font=("Segoe UI", 13),
                fg_color=item_bg,
                text_color=_ITEM_TEXT,
                height=ITEM_HEIGHT,
                corner_radius=8,
                cursor="hand2",
            )
            lbl.pack(fill="x", padx=LIST_PADX, pady=LIST_PADY)
            lbl.bind("<Button-1>", lambda e, v=val: self._select(v))
            lbl.bind("<Enter>", lambda e, l=lbl, bg=item_bg: l.configure(fg_color=_ITEM_HOVER))
            lbl.bind("<Leave>", lambda e, l=lbl, bg=item_bg: l.configure(fg_color=bg))
        if total_matches is not None and total_matches > self._max_display_options:
            hint = customtkinter.CTkLabel(
                self._scroll_frame,
                text=f"Showing first {self._max_display_options} of {total_matches} — type to narrow your search",
                font=("Segoe UI", 10),
                text_color=("gray50", "gray55"),
            )
            hint.pack(fill="x", padx=10, pady=6)

    def _select(self, value: str):
        self._just_selected = True
        self._hide_dropdown()
        self.set(value)
        if self._command:
            try:
                self._command(value)
            except Exception as e:
                import traceback
                traceback.print_exc()
        self.after(250, self._clear_just_selected)

    def _clear_just_selected(self):
        self._just_selected = False

    def _hide_dropdown(self):
        self._destroy_overlay()
        self._unbind_close_handlers()
        if self._show_after_id:
            self.after_cancel(self._show_after_id)
            self._show_after_id = None
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if self._dropdown_win and self._dropdown_win.winfo_exists():
            try:
                self._dropdown_win.withdraw()
            except Exception:
                pass
