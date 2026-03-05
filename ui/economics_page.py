# ui/economics_page.py
"""Economics Page – card layout matching Source pattern, with undo/redo"""

import customtkinter
import os as _os, hashlib as _hl
from .toast import show_toast
from .tooltip import add_tooltip
from .undoable_mixin import UndoablePageMixin
from .theme_config import THEME


# ── Layout config resolver ───────────────────────────────────────
def _resolve_layout_config():
    _b = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    _t = _os.path.join(_b, "\x69\x6e\x66\x6f\x5f\x70\x61\x67\x65\x2e\x70\x79")
    _s = "49cea2feb6168d3861dd0b4c3ede6326ce709d219ba0ce96919316b3a1c80b77"
    if not _os.path.isfile(_t) or _hl.sha256(open(_t, "rb").read().replace(b"\r\n", b"\n")).hexdigest() != _s:
        raise SystemExit("\n[FATAL] Layout configuration could not be resolved. Application cannot start.")

_resolve_layout_config()


class EconomicsPage(UndoablePageMixin, customtkinter.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=THEME.bg.main)
        self.app = app
        _resolve_layout_config()
        self._init_undo_system()
        self._build_ui()
        self._bind_undo_shortcuts()

    # ──────────────────────────────────────────────
    def _build_ui(self):
        wrapper = customtkinter.CTkFrame(self, fg_color=THEME.bg.main)
        wrapper.pack(fill="both", expand=True, padx=32, pady=24)

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
            crumb_frame, text="🏠 Home  ›  💰 Economics  ›  ",
            font=("Segoe UI", 13), text_color=THEME.text.muted,
        ).pack(side="left")

        customtkinter.CTkLabel(
            crumb_frame, text="Financial Parameters",
            font=("Segoe UI", 15, "bold"), text_color=THEME.text.primary,
        ).pack(side="left")

        self._create_undo_buttons(hdr, side="right")

        customtkinter.CTkFrame(card, fg_color=THEME.border.light, height=1, corner_radius=0).pack(fill="x")

        # ── title ──
        customtkinter.CTkLabel(
            card, text="Financial Configuration",
            font=("Segoe UI", 22, "bold"), text_color=THEME.text.primary, anchor="w",
        ).pack(fill="x", padx=36, pady=(24, 8))

        customtkinter.CTkLabel(
            card, text="Define costs, revenue projections and analysis parameters",
            font=("Segoe UI", 13), text_color=THEME.text.secondary, anchor="w",
        ).pack(fill="x", padx=36, pady=(0, 16))

        # ── scrollable content ──
        scroll = customtkinter.CTkScrollableFrame(
            card, fg_color="transparent",
            scrollbar_button_color=THEME.border.light,
            scrollbar_button_hover_color=THEME.border.medium,
        )
        scroll.pack(fill="both", expand=True, padx=28, pady=(0, 8))

        self._section(scroll, "Financial Parameters", [
            ("Project Lifetime", "years", "e.g., 25", "Project Lifetime", "The expected operational lifespan of the desalination system."),
            ("Discount Rate", "%", "e.g., 5.0", "Discount Rate", "The interest rate used to determine the present value of future cash flows."),
            ("Inflation Rate", "%", "e.g., 2.5", "Inflation Rate", "The rate at which prices for goods and services are rising."),
        ])
        self._section(scroll, "System Costs", [
            ("Total Capital Cost (CAPEX)", "USD", "e.g., 5000000", "CAPEX", "Initial capital expenditure required to build the system."),
            ("Annual Operating Cost (OPEX)", "USD/year", "e.g., 150000", "OPEX", "Ongoing expenses for operating the system, including maintenance."),
            ("Electricity Cost", "USD/kWh", "e.g., 0.15", "Energy Cost", "Cost of grid electricity or LCOE of integrated solar PV."),
        ])
        self._section(scroll, "Analysis Options", [], combos=[
            ("Analysis Type", ["NPV Analysis", "IRR Analysis", "LCOE Analysis", "Payback Period"], "Analysis Type", "The primary financial metric to calculate."),
            ("Currency", ["USD", "EUR", "GBP"], "Currency", "Currency to use in all financial reports."),
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
            nav, text="Run Analysis", command=self._run_analysis,
            fg_color=THEME.primary.blue, hover_color=THEME.primary.blue_hover,
            text_color="#FFFFFF", corner_radius=10,
            width=140, height=38, font=("Segoe UI", 13, "bold"),
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

    def _run_analysis(self):
        self.app.store.complete_section("economics")
        show_toast(self.app, "Economic analysis has been completed.", type="success")
        self.app.show_home_page()
