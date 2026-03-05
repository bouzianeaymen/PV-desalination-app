# ui/source/main.py
# Main container for Source workflow – combines all step mixins

import sys
import os
import io
import math
import threading
import pandas as pd
import numpy as np
import calendar
import logging

logger = logging.getLogger(__name__)

# Ensure project root is on path so "source" (panel_data, energy_models) can be imported
# regardless of how the app is launched (app.py, IDE Run, or other entry point).
_this_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_this_dir))  # ui/source -> ui -> project root
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import customtkinter
import tkinter
from tkinter import filedialog
from .constants import *
from .components import create_visualize_card, create_kpi_card
from .step1_import import Step1ImportMixin
from .step2_visualize import Step2VisualizeMixin
from .source_page_energy import SourcePageEnergyMixin
from .searchable_dropdown import SearchableDropdown

# Import panel list and TC/Ppv models separately so one failure does not clear all lists.
load_panels = get_manufacturers = get_curated_manufacturers = get_models_by_manufacturer = None
get_panel_params = get_panel_params_full = format_panel_summary = None
TC_MODELS = {}
PPV_MODELS = {}
run_energy_calculation = None
fetch_fixed_mounting_hourly = None

try:
    from source.panel_data import (
        load_panels,
        build_panel_index,
        get_manufacturers,
        get_curated_manufacturers,
        get_models_by_manufacturer,
        get_panel_params,
        get_panel_params_full,
        format_panel_summary,
        get_manufacturers_matching,
        get_combined_panel_results,
        parse_combined_selection,
    )
except Exception as e:
    logger.error("Source step (panel_data) import failed", exc_info=True)

try:
    from source.energy_models import (
    TC_MODELS,
    PPV_MODELS,
    run_energy_calculation,
    aggregate_energy_hourly,
    prepare_energy_table_data,
)
except Exception as e:
    logger.error("Source step (energy_models) import failed", exc_info=True)
    TC_MODELS = {}
    PPV_MODELS = {}
    run_energy_calculation = None
    aggregate_energy_hourly = None
    prepare_energy_table_data = None

try:
    from source.fetch_fixed import fetch_fixed_mounting_hourly
except Exception as e:
    logger.warning("Source step (fetch_fixed) import failed; tracking Kt will use fixed=x fallback: %s", e)
    fetch_fixed_mounting_hourly = None

try:
    from .equation_renderer import (
        TC_LATEX,
        PPV_LATEX,
        render_equations_to_image,
        format_constants_card,
    )
except Exception:
    TC_LATEX = {}
    PPV_LATEX = {}
    render_equations_to_image = None
    format_constants_card = None


class SourcePage(Step1ImportMixin, Step2VisualizeMixin, SourcePageEnergyMixin, customtkinter.CTkFrame):
    """
    Main container for Source workflow.
    Manages navigation between steps and shared state.
    """

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.current_step = 1
        self.step1_completed = False
        self.import_config = None
        self.next_button = None
        self.back_button = None
        self.nav_frame = None
        self.source_specific_frame = None
        self.pvgis_body_frame = None
        self.pvgis_mode_var = tkinter.StringVar(value="HOURLY")
        self.ninja_mode_var = tkinter.StringVar(value="PV")
        self.store_in_project_var = tkinter.BooleanVar(value=True)

        self.configure(fg_color=BG_MAIN)
        self.step_items = []

        self._build_layout()
        self._update_step_visuals()
        self._update_content()

    # ──────────────────────────────────────────────
    # Layout
    # ──────────────────────────────────────────────
    def _build_layout(self):
        """Single card layout: stepper → title → scrollable content → nav bar."""

        # outer padding
        wrapper = customtkinter.CTkFrame(self, fg_color=BG_MAIN)
        wrapper.pack(fill="both", expand=True, padx=32, pady=24)

        # card
        self.content_panel = customtkinter.CTkFrame(
            wrapper, fg_color=BG_CARD, corner_radius=18,
            border_width=1, border_color=THEME.border.light,
        )
        self.content_panel.pack(fill="both", expand=True)

        # ── top: stepper bar ──
        stepper_bar = customtkinter.CTkFrame(
            self.content_panel, fg_color=THEME.bg.gray_pale,
            corner_radius=0, height=52,
        )
        stepper_bar.pack(fill="x")
        stepper_bar.pack_propagate(False)

        # round the top corners manually by clipping with the card
        # (CTk renders children inside parent corner_radius automatically)

        self._build_stepper(stepper_bar)

        # thin divider below stepper
        customtkinter.CTkFrame(
            self.content_panel, fg_color=THEME.border.light, height=1, corner_radius=0,
        ).pack(fill="x")

        # ── title ──
        self.title_label = customtkinter.CTkLabel(
            self.content_panel,
            text=STEP_CONTENT_TITLES[1],
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=36, pady=(24, 12))

        # ── scrollable content ──
        self.content_inner = customtkinter.CTkFrame(
            self.content_panel, fg_color="transparent",
        )
        self.content_inner.pack(fill="both", expand=True, padx=36, pady=(0, 8))

        # ── bottom nav bar ──
        customtkinter.CTkFrame(
            self.content_panel, fg_color=THEME.border.light, height=1, corner_radius=0,
        ).pack(fill="x", padx=32)

        self.nav_frame = customtkinter.CTkFrame(
            self.content_panel, fg_color="transparent", height=72,
        )
        self.nav_frame.pack(fill="x", padx=32, pady=(4, 8))
        self.nav_frame.pack_propagate(False)

        # Back – soft fill, no border (secondary recedes)
        self.back_button = customtkinter.CTkButton(
            self.nav_frame,
            text="← Back",
            command=self._on_back,
            fg_color=THEME.bg.hover,
            hover_color=THEME.border.light,
            text_color=THEME.text.secondary,
            border_width=0,
            corner_radius=10,
            width=110,
            height=40,
            font=("Segoe UI", 13),
        )
        self.back_button.pack(side="left", pady=16)

        # Next/Finish – wider, bolder (primary pops)
        self.next_button = customtkinter.CTkButton(
            self.nav_frame,
            text="Next →",
            command=self._on_next,
            fg_color=THEME.bg.disabled,
            hover_color=THEME.primary.blue_hover,
            text_color=THEME.text.muted,
            corner_radius=10,
            width=150,
            height=40,
            font=("Segoe UI", 14, "bold"),
            state="disabled",
        )
        self.next_button.pack(side="right", pady=16)

    # ──────────────────────────────────────────────
    # Horizontal stepper
    # ──────────────────────────────────────────────
    def _build_stepper(self, parent):
        row = customtkinter.CTkFrame(parent, fg_color="transparent")
        row.pack(expand=True, padx=32)

        steps = [("1", "Import Data"), ("2", "Energy")]
        for i, (num, label) in enumerate(steps):
            sf = customtkinter.CTkFrame(row, fg_color="transparent")
            sf.pack(side="left", padx=8)

            circ = customtkinter.CTkLabel(
                sf, text=num, width=30, height=30, corner_radius=15,
                fg_color=THEME.border.light, text_color=THEME.text.muted,
                font=("Segoe UI", 13, "bold"),
            )
            circ.pack(side="left")

            lbl = customtkinter.CTkLabel(
                sf, text=label,
                font=("Segoe UI", 13), text_color=THEME.text.muted,
            )
            lbl.pack(side="left", padx=(10, 0))

            self.step_items.append({"circle": circ, "label": lbl})

            if i < len(steps) - 1:
                customtkinter.CTkFrame(
                    row, fg_color=THEME.border.medium, width=48, height=2,
                ).pack(side="left", padx=6, pady=14)

    # ──────────────────────────────────────────────
    # Step visuals
    # ──────────────────────────────────────────────
    def _update_step_visuals(self):
        for i, item in enumerate(self.step_items, start=1):
            if i == self.current_step:
                item["circle"].configure(fg_color=PRIMARY_BLUE, text_color="#FFFFFF")
                item["label"].configure(text_color=THEME.text.primary, font=("Segoe UI", 13, "bold"))
            elif i == 1 and self.app.source_config_cache.get("import_success"):
                item["circle"].configure(fg_color=SUCCESS_GREEN, text_color="#FFFFFF")
                item["label"].configure(text_color=SUCCESS_GREEN, font=("Segoe UI", 13, "bold"))
            else:
                item["circle"].configure(fg_color=THEME.border.light, text_color=THEME.text.muted)
                item["label"].configure(text_color=THEME.text.muted, font=("Segoe UI", 13))

    # ──────────────────────────────────────────────
    # Content switching
    # ──────────────────────────────────────────────
    def _update_content(self):
        for child in self.content_inner.winfo_children():
            child.destroy()

        self.title_label.configure(text=STEP_CONTENT_TITLES.get(self.current_step, ""))

        if self.current_step == 1:
            self._build_step1_form()
            self._update_next_button_state()
        elif self.current_step == 2:
            if not self.step1_completed:
                # Empty state with icon and message
                empty = customtkinter.CTkFrame(self.content_inner, fg_color="transparent")
                empty.pack(expand=True)
                customtkinter.CTkLabel(
                    empty, text="📊", font=("Segoe UI", 48),
                    text_color=THEME.text.muted,
                ).pack(pady=(0, 12))
                customtkinter.CTkLabel(
                    empty, text="No data imported yet",
                    font=("Segoe UI", 18, "bold"), text_color=THEME.text.secondary,
                ).pack(pady=(0, 8))
                customtkinter.CTkLabel(
                    empty, text="Complete Step 1 to import data,\nthen return here for Energy (TC & Ppv models).",
                    font=("Segoe UI", 13), text_color=THEME.text.muted,
                    justify="center",
                ).pack()
                self._set_next_button_state("disabled")
            else:
                self._build_step2_energy()
                self._set_finish_button_state()
                if hasattr(self, "_update_energy_visualize_export_button_state"):
                    self._update_energy_visualize_export_button_state()

        if self.next_button:
            self.next_button.configure(text="Finish →" if self.current_step == 2 else "Next →")

    # ──────────────────────────────────────────────
    # Button helpers
    # ──────────────────────────────────────────────
    def _set_next_button_state(self, state):
        if not self.next_button:
            return
        if state == "disabled":
            self.next_button.configure(
                state="disabled",
                fg_color=THEME.bg.disabled,
                text_color=THEME.text.muted,
            )
        else:
            self.next_button.configure(
                state="normal",
                fg_color=PRIMARY_BLUE,
                text_color="#FFFFFF",
                hover_color=PRIMARY_HOVER,
            )

    def _set_finish_button_state(self):
        if not self.next_button:
            return
        self.next_button.configure(
            state="normal",
            fg_color=SUCCESS_GREEN,
            hover_color=SUCCESS_DARK,
            text_color="#FFFFFF",
        )

    def _update_next_button_state(self):
        if self.current_step == 1:
            self._set_next_button_state("normal" if self.step1_completed else "disabled")
            # Ensure button text is "Next" on step 1
            if self.next_button:
                self.next_button.configure(text="Next →")
        if hasattr(self, "_update_visualize_export_button_state"):
            self._update_visualize_export_button_state()

    def _open_visualize_export_popup(self):
        """Open Visualize & Export (Summary, Data Tables, Export) in a popup window."""
        if not self.step1_completed:
            return
        popup = customtkinter.CTkToplevel(self)
        popup.title("Visualize & Export")
        popup.geometry("900x600")
        popup.configure(fg_color=THEME.bg.main)
        try:
            popup.transient(self.winfo_toplevel())
        except Exception:
            pass
        self._visualize_export_modal_root = popup

        def on_popup_close():
            self._visualize_export_modal_root = None
            try:
                popup.destroy()
            except Exception:
                pass

        try:
            popup.protocol("WM_DELETE_WINDOW", on_popup_close)
        except Exception:
            pass

        inner = customtkinter.CTkFrame(popup, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=24)
        self._build_step2_outputs(parent=inner)

    # ──────────────────────────────────────────────
    # Navigation
    # ──────────────────────────────────────────────
    def _on_back(self):
        if self.current_step == 1:
            self.app.show_home_page()
        else:
            if self.current_step == 2:
                self._save_energy_selections()
            self.current_step -= 1
            self._update_step_visuals()
            self._update_content()

    def _on_next(self):
        if self.current_step == 1:
            if not self.step1_completed:
                if hasattr(self, "status_label"):
                    self.status_label.configure(
                        text="Please import data successfully before proceeding.",
                        text_color=ERROR_RED,
                    )
                return
            self._cache_step1_inputs()
            self.current_step += 1
            self._update_step_visuals()
            self._update_content()
        elif self.current_step == 2:
            self._finish_source_workflow()
