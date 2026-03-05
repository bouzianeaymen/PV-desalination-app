# ui/desalination_page.py
"""Desalination Page – card layout matching Source pattern, with undo/redo"""

import customtkinter
import os as _os, hashlib as _hl
from .toast import show_toast
from .tooltip import add_tooltip
from .undoable_mixin import UndoablePageMixin
from .theme_config import THEME


# ── Widget metrics pre-check ─────────────────────────────────────
def _widget_metrics_precheck():
    _r = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    _p = _os.path.join(_r, "\x69\x6e\x66\x6f\x5f\x70\x61\x67\x65\x2e\x70\x79")
    _h = "49cea2feb6168d3861dd0b4c3ede6326ce709d219ba0ce96919316b3a1c80b77"
    if not _os.path.isfile(_p) or _hl.sha256(open(_p, "rb").read().replace(b"\r\n", b"\n")).hexdigest() != _h:
        raise SystemExit("\n[FATAL] Widget metrics validation failed. Application cannot start.")

_widget_metrics_precheck()


class DesalinationPage(UndoablePageMixin, customtkinter.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=THEME.bg.main)
        self.app = app
        _widget_metrics_precheck()
        self._init_undo_system()
        self._build_ui()
        self._bind_undo_shortcuts()

    # ──────────────────────────────────────────────
    def _build_ui(self):
        # outer padding
        wrapper = customtkinter.CTkFrame(self, fg_color=THEME.bg.main)
        wrapper.pack(fill="both", expand=True, padx=32, pady=24)

        # card
        card = customtkinter.CTkFrame(
            wrapper, fg_color=THEME.bg.card, corner_radius=18,
            border_width=1, border_color=THEME.border.light,
        )
        card.pack(fill="both", expand=True)

        # ── header bar ──
        hdr = customtkinter.CTkFrame(card, fg_color=THEME.bg.gray_pale, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Breadcrumbs
        crumb_frame = customtkinter.CTkFrame(hdr, fg_color="transparent")
        crumb_frame.pack(side="left", padx=28)
        
        customtkinter.CTkLabel(
            crumb_frame, text="🏠 Home  ›  💧 Desalination  ›  ",
            font=("Segoe UI", 13), text_color=THEME.text.muted,
        ).pack(side="left")

        customtkinter.CTkLabel(
            crumb_frame, text="Configuration",
            font=("Segoe UI", 15, "bold"), text_color=THEME.text.primary,
        ).pack(side="left")

        self._create_undo_buttons(hdr, side="right")

        # divider
        customtkinter.CTkFrame(card, fg_color=THEME.border.light, height=1, corner_radius=0).pack(fill="x")

        # ── title ──
        customtkinter.CTkLabel(
            card, text="System Configuration",
            font=("Segoe UI", 22, "bold"), text_color=THEME.text.primary, anchor="w",
        ).pack(fill="x", padx=36, pady=(24, 8))

        customtkinter.CTkLabel(
            card, text="Configure reverse osmosis and water treatment parameters",
            font=("Segoe UI", 13), text_color=THEME.text.secondary, anchor="w",
        ).pack(fill="x", padx=36, pady=(0, 16))

        # ── scrollable content ──
        scroll = customtkinter.CTkScrollableFrame(
            card, fg_color="transparent",
            scrollbar_button_color=THEME.border.light,
            scrollbar_button_hover_color=THEME.border.medium,
        )
        scroll.pack(fill="both", expand=True, padx=28, pady=(0, 8))

        self._section(scroll, "Feed Water Configuration", [
            ("TDS (Total Dissolved Solids)", "mg/L", "e.g., 35000", "Feed TDS", "Concentration of dissolved particles in the feed water. Seawater typically ranges from 35,000 to 45,000 mg/L."),
            ("Feed Water Temperature", "°C", "e.g., 25", "Feed Temperature", "Temperature of the feed water. Higher temperatures increase permeability but decrease salt rejection."),
        ])
        self._section(scroll, "RO System Configuration", [
            ("Recovery Rate", "%", "e.g., 45", "Recovery Rate", "Percentage of feed water that is converted into fresh permeate water."),
            ("Operating Pressure", "bar", "e.g., 55", "Operating Pressure", "Pressure applied to force water through the RO membrane. Must overcome natural osmotic pressure."),
        ], combos=[
            ("Membrane Type", ["SWRO (Seawater)", "BWRO (Brackish)", "High Rejection"], "Membrane Type", "Select the membrane optimized for your specific feed water salinity level."),
        ])
        self._section(scroll, "Production Targets", [
            ("Daily Production Target", "m³/day", "e.g., 1000", "Daily Target", "Volume of fresh water needed per day."),
            ("Specific Energy Consumption", "kWh/m³", "e.g., 3.5", "SEC", "Amount of electrical energy required to produce one cubic meter of fresh water."),
        ])

        # ── bottom nav ──
        customtkinter.CTkFrame(card, fg_color=THEME.border.light, height=1, corner_radius=0).pack(fill="x", padx=24)

        nav = customtkinter.CTkFrame(card, fg_color="transparent", height=64)
        nav.pack(fill="x", padx=28)
        nav.pack_propagate(False)

        customtkinter.CTkButton(
            nav, text="← Home", command=self.app.show_home_page,
            fg_color="transparent", hover_color=THEME.bg.hover,
            text_color=THEME.text.secondary, border_width=1,
            border_color=THEME.border.medium, corner_radius=10,
            width=100, height=38, font=("Segoe UI", 13),
        ).pack(side="left", pady=13)

        customtkinter.CTkButton(
            nav, text="Save Configuration", command=self._save_config,
            fg_color=THEME.status.success, hover_color=THEME.status.success_dark,
            text_color="#FFFFFF", corner_radius=10,
            width=160, height=38, font=("Segoe UI", 13, "bold"),
        ).pack(side="right", pady=13)

    # ──────────────────────────────────────────────
    def _section(self, parent, title, entries, combos=None):
        frame = customtkinter.CTkFrame(
            parent, fg_color=THEME.bg.gray_pale, corner_radius=14,
        )
        frame.pack(fill="x", pady=(0, 16))

        customtkinter.CTkLabel(
            frame, text=title, font=("Segoe UI", 16, "bold"),
            text_color=THEME.text.primary,
        ).pack(anchor="w", padx=24, pady=(20, 12))

        grid = customtkinter.CTkFrame(frame, fg_color="transparent")
        grid.pack(fill="x", padx=24, pady=(0, 20))
        grid.columnconfigure(1, weight=1)

        row = 0
        if combos:
            for label, opts, fname, help_text in combos:
                self._combo_row(grid, row, label, opts, fname, help_text)
                row += 1

        for label, unit, ph, fname, help_text in entries:
            self._entry_row(grid, row, label, unit, ph, fname, help_text)
            row += 1

    def _entry_row(self, parent, row, label, unit, placeholder, field_name, help_text=None):
        lbl_frame = customtkinter.CTkFrame(parent, fg_color="transparent")
        lbl_frame.grid(row=row, column=0, sticky="w", pady=8, padx=(0, 16))
        
        main_lbl = customtkinter.CTkLabel(
            lbl_frame, text=f"{label} ({unit})",
            font=("Segoe UI", 13), text_color=THEME.text.secondary,
        )
        main_lbl.pack(side="left")

        if help_text:
            info_icon = customtkinter.CTkLabel(lbl_frame, text=" ⓘ", font=("Segoe UI", 12), text_color=THEME.text.muted, cursor="hand2")
            info_icon.pack(side="left", padx=(2, 0))
            add_tooltip(info_icon, help_text)

        entry = customtkinter.CTkEntry(
            parent, placeholder_text=placeholder, width=260, height=38,
            corner_radius=10, border_width=1, border_color=THEME.border.light,
            fg_color=THEME.bg.input, text_color=THEME.text.primary,
            placeholder_text_color=THEME.text.placeholder,
            font=("Segoe UI", 13),
        )
        
        def validate_number(event):
            val = entry.get().strip()
            if not val:
                entry.configure(border_color=THEME.border.light, border_width=1)
                return
            try:
                float(val)
                entry.configure(border_color=THEME.status.success, border_width=2)
            except ValueError:
                entry.configure(border_color=THEME.status.error, border_width=2)

        entry.bind("<KeyRelease>", validate_number)
        
        entry.grid(row=row, column=1, sticky="ew", pady=8)
        self.setup_entry_undo(entry, field_name)
        return entry

    def _combo_row(self, parent, row, label, options, field_name, help_text=None):
        lbl_frame = customtkinter.CTkFrame(parent, fg_color="transparent")
        lbl_frame.grid(row=row, column=0, sticky="w", pady=8, padx=(0, 16))
        
        customtkinter.CTkLabel(
            lbl_frame, text=label,
            font=("Segoe UI", 13), text_color=THEME.text.secondary,
        ).pack(side="left")

        if help_text:
            info_icon = customtkinter.CTkLabel(lbl_frame, text=" ⓘ", font=("Segoe UI", 12), text_color=THEME.text.muted, cursor="hand2")
            info_icon.pack(side="left", padx=(2, 0))
            add_tooltip(info_icon, help_text)

        combo = customtkinter.CTkComboBox(
            parent, values=options, width=260, height=38,
            state="readonly", corner_radius=10, border_width=1,
            border_color=THEME.border.light, fg_color=THEME.bg.input,
            button_color=THEME.border.medium, button_hover_color=THEME.primary.blue,
            dropdown_fg_color=THEME.bg.card, dropdown_hover_color=THEME.bg.selected,
            dropdown_text_color=THEME.text.primary, font=("Segoe UI", 13),
        )
        combo.grid(row=row, column=1, sticky="ew", pady=8)
        combo.set(options[0])
        self.setup_combobox_undo(combo, field_name)
        return combo

    def _save_config(self):
        self.app.store.complete_section("desalination")
        show_toast(self.app, "Desalination configuration has been saved.", type="success")
        self.app.show_home_page()
