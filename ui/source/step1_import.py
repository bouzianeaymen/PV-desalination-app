# ui/source/step1_import.py
# Step 1: Import Data - All form building and API import logic

import customtkinter
import tkinter
import pandas as pd
import numpy as np
import threading
from .constants import *

# Import metadata discovery
try:
    from source.api_metadata_discovery import metadata_discovery
except ImportError:
    # Fallback if discovery module fails
    class DummyDiscovery:
        def get_range_for_dataset(self, source_type, dataset_name):
            if source_type == "pvgis":
                return {"min": 2005, "max": 2023, "source": "fallback"}
            elif source_type == "ninja":
                if "sarah" in dataset_name.lower():
                    return {"min": 2005, "max": 2020, "source": "fallback"}
                return {"min": 1980, "max": 2023, "source": "fallback"}
            return {"min": 2000, "max": 2023, "source": "fallback"}
    metadata_discovery = DummyDiscovery()


class Step1ImportMixin:
    """
    Step 1: Import Data functionality
    Contains all methods for PVGIS Hourly, PVGIS TMY, and Renewables.ninja API calls
    """
    
    def _build_step1_form(self):
        """Build Step 1 form inside content_inner only"""
        scroll_frame = customtkinter.CTkScrollableFrame(
            self.content_inner, fg_color="transparent",
            scrollbar_button_color=THEME.border.gray, scrollbar_button_hover_color=THEME.border.medium
        )
        scroll_frame.pack(fill="both", expand=True)
        self._step1_scroll_frame = scroll_frame
        
        subtitle = customtkinter.CTkLabel(
            scroll_frame, text="Configure site and data source",
            font=(FONT_FAMILY_TEXT, 13), text_color=TEXT_SECONDARY
        )
        subtitle.pack(anchor="w", pady=(0, 16))
        
        src_frame = customtkinter.CTkFrame(scroll_frame, fg_color="transparent")
        src_frame.pack(fill="x", pady=(0, 12))
        
        src_label = customtkinter.CTkLabel(
            src_frame, text="Data source *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        src_label.pack(anchor="w")
        
        self.src_combo = customtkinter.CTkComboBox(
            src_frame, values=["PVGIS", "Renewables Ninja"], 
            width=COMBO_WIDTH, state="readonly", command=self._on_source_change
        )
        self.src_combo.set("PVGIS")
        self.src_combo.pack(anchor="w", pady=(4, 0))
        
        self.source_specific_frame = customtkinter.CTkFrame(
            scroll_frame, fg_color="transparent"
        )
        self.source_specific_frame.pack(fill="x", pady=(10, 0))
        
        current_source = self.src_combo.get()
        if current_source == "PVGIS":
            self._build_pvgis_form()
        else:
            self._build_ninja_form()
        
        # Actions frame (Import button + Status)
        actions_frame = customtkinter.CTkFrame(scroll_frame, fg_color="transparent")
        actions_frame.pack(fill="x", pady=(20, 10))
        
        self.status_label = customtkinter.CTkLabel(
            actions_frame, text="Fill in all required fields and click Import data.",
            font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        self.status_label.pack(side="left")
        
        self.visualize_export_button = customtkinter.CTkButton(
            actions_frame, text="Visualize & Export", command=self._on_visualize_export_click,
            fg_color=THEME.bg.disabled, hover_color=THEME.border.light, text_color=THEME.text.muted,
            corner_radius=CORNER_RADIUS_BUTTON, width=140, height=32, state="disabled",
        )
        self.visualize_export_button.pack(side="right", padx=(8, 0))

        self.import_button = customtkinter.CTkButton(
            actions_frame, text="Import data", command=self._on_import_data,
            fg_color=PRIMARY_BLUE, hover_color=PRIMARY_HOVER, text_color="#FFFFFF",
            corner_radius=CORNER_RADIUS_BUTTON, width=120, height=32
        )
        self.import_button.pack(side="right")
        
        # Restore cached inputs if available
        self._restore_step1_inputs()

    def _on_source_change(self, choice):
        if getattr(self, '_is_restoring', False):
            for child in self.source_specific_frame.winfo_children():
                child.destroy()
            if choice == "PVGIS":
                self._build_pvgis_form()
            else:
                self._build_ninja_form()
            return
        # Cache current form state before destroying (preserves data when switching sources)
        self._cache_step1_inputs()
        self.step1_completed = False
        self._cached_hourly_df = None
        self._cached_monthly_df = None
        self._cached_yearly_df = None
        if hasattr(self, "status_label"):
            self.status_label.configure(
                text="Fill in all required fields and click Import data.",
                text_color=TEXT_SECONDARY
            )
        self._update_next_button_state()
        self._update_visualize_export_button_state()

        for child in self.source_specific_frame.winfo_children():
            child.destroy()

        if choice == "PVGIS":
            self._build_pvgis_form()
        else:
            self._build_ninja_form()
        
        # Scroll to top for consistent exploration when switching sources
        try:
            sf = getattr(self, '_step1_scroll_frame', None)
            if sf and sf.winfo_exists():
                canvas = getattr(sf, '_parent_canvas', None) or getattr(sf, 'parent_canvas', None)
                if canvas:
                    canvas.yview_moveto(0)
        except Exception:
            pass

    def _update_visualize_export_button_state(self):
        """Enable Visualize & Export button only after successful import."""
        if not hasattr(self, "visualize_export_button") or not self.visualize_export_button.winfo_exists():
            return
        if self.step1_completed:
            self.visualize_export_button.configure(
                state="normal",
                fg_color=PRIMARY_BLUE,
                hover_color=PRIMARY_HOVER,
                text_color="#FFFFFF",
            )
        else:
            self.visualize_export_button.configure(
                state="disabled",
                fg_color=THEME.bg.disabled,
                text_color=THEME.text.muted,
            )

    def _on_visualize_export_click(self):
        """Open Visualize & Export in a popup (called from SourcePage._open_visualize_export_popup)."""
        self._open_visualize_export_popup()

    def _on_pvgis_mounting_change(self, *args):
        """
        Handle mounting type changes.
        Updates slope/azimuth field states based on mounting type:
        - Fixed: Both enabled, optimization checkboxes available
        - Vertical axis: Slope enabled, azimuth disabled
        - Inclined axis: Both disabled
        - Two axis: Both disabled
        """
        mounting = self.pvgis_mount_var.get()
        
        # Check if widgets exist (they may not exist during initial form build)
        has_slope = hasattr(self, 'pvgis_slope') and self.pvgis_slope.winfo_exists()
        has_azimuth = hasattr(self, 'pvgis_azimuth') and self.pvgis_azimuth.winfo_exists()
        has_opt_slope = hasattr(self, 'opt_slope_cb') and self.opt_slope_cb.winfo_exists()
        has_opt_azimuth = hasattr(self, 'opt_azimuth_cb') and self.opt_azimuth_cb.winfo_exists()
        
        if mounting == "fixed":
            # Fixed: Both fields enabled, optimization checkboxes available
            if has_slope:
                self.pvgis_slope.configure(state="normal", fg_color=(BG_INPUT_FOCUS, "#2B2B2B"))
            if has_azimuth:
                self.pvgis_azimuth.configure(state="normal", fg_color=(BG_INPUT_FOCUS, "#2B2B2B"))
            if has_opt_slope:
                self.opt_slope_cb.configure(state="normal")
            if has_opt_azimuth:
                self.opt_azimuth_cb.configure(state="normal")
            if hasattr(self, "pvgis_slope_label") and self.pvgis_slope_label.winfo_exists():
                self.pvgis_slope_label.configure(text="Slope [°]")
                
        elif mounting == "vertical_axis":
            # Vertical axis: Slope enabled (optional), azimuth disabled
            if has_slope:
                self.pvgis_slope.configure(state="normal", fg_color=(BG_INPUT_FOCUS, "#2B2B2B"))
            if hasattr(self, "pvgis_slope_label") and self.pvgis_slope_label.winfo_exists():
                self.pvgis_slope_label.configure(text="Slope [°] (optional)")
            if has_azimuth:
                self.pvgis_azimuth.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
                self.pvgis_azimuth.delete(0, 'end')
                self.pvgis_azimuth.insert(0, "0")  # Default for vertical axis
            if has_opt_slope:
                self.opt_slope_cb.configure(state="disabled")
                self.pvgis_opt_slope_var.set(False)
            if has_opt_azimuth:
                self.opt_azimuth_cb.configure(state="disabled")
                self.pvgis_opt_azimuth_var.set(False)
                
        elif mounting == "inclined_axis":
            # Inclined axis: Both disabled, clear values so they are not sent
            if has_slope:
                self.pvgis_slope.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
                self.pvgis_slope.delete(0, "end")
            if has_azimuth:
                self.pvgis_azimuth.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
                self.pvgis_azimuth.delete(0, "end")
            if has_opt_slope:
                self.opt_slope_cb.configure(state="disabled")
                self.pvgis_opt_slope_var.set(False)
            if has_opt_azimuth:
                self.opt_azimuth_cb.configure(state="disabled")
                self.pvgis_opt_azimuth_var.set(False)
            if hasattr(self, "pvgis_slope_label") and self.pvgis_slope_label.winfo_exists():
                self.pvgis_slope_label.configure(text="Slope [°]")
                
        elif mounting == "two_axis":
            # Two axis: Both disabled, clear values so they are not sent
            if has_slope:
                self.pvgis_slope.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
                self.pvgis_slope.delete(0, "end")
            if has_azimuth:
                self.pvgis_azimuth.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
                self.pvgis_azimuth.delete(0, "end")
            if has_opt_slope:
                self.opt_slope_cb.configure(state="disabled")
                self.pvgis_opt_slope_var.set(False)
            if has_opt_azimuth:
                self.opt_azimuth_cb.configure(state="disabled")
                self.pvgis_opt_azimuth_var.set(False)
            if hasattr(self, "pvgis_slope_label") and self.pvgis_slope_label.winfo_exists():
                self.pvgis_slope_label.configure(text="Slope [°]")

    def _on_pvgis_optimize_change(self):
        """Handle show/hide of tilt/azimuth fields based on optimization checkboxes."""
        # Only apply optimization logic for fixed mounting
        if hasattr(self, 'pvgis_mount_var') and self.pvgis_mount_var.get() != "fixed":
            return
            
        opt_slope = self.pvgis_opt_slope_var.get()
        opt_azimuth = self.pvgis_opt_azimuth_var.get()
        # Make mutually exclusive: checking "Optimize tilt" unchecks "Optimize tilt and azimuth"
        if opt_slope and opt_azimuth:
            self.pvgis_opt_azimuth_var.set(False)
            opt_azimuth = False
        
        # Check if widgets exist
        has_slope = hasattr(self, 'pvgis_slope') and self.pvgis_slope.winfo_exists()
        has_azimuth = hasattr(self, 'pvgis_azimuth') and self.pvgis_azimuth.winfo_exists()
        
        if opt_azimuth:
            if has_slope:
                self.pvgis_slope.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
            if has_azimuth:
                self.pvgis_azimuth.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
            if opt_slope:
                self.pvgis_opt_slope_var.set(False)
        elif opt_slope:
            if has_slope:
                self.pvgis_slope.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
            if has_azimuth:
                self.pvgis_azimuth.configure(state="normal", fg_color=(BG_INPUT_FOCUS, "#2B2B2B"))
        else:
            if has_slope:
                self.pvgis_slope.configure(state="normal", fg_color=(BG_INPUT_FOCUS, "#2B2B2B"))
            if has_azimuth:
                self.pvgis_azimuth.configure(state="normal", fg_color=(BG_INPUT_FOCUS, "#2B2B2B"))

    def _on_ninja_optimize_change(self):
        """Handle show/hide of tilt/azimuth fields based on optimization checkbox."""
        use_optimal = self.ninja_opt_angles_var.get()
        
        if use_optimal:
            self.ninja_tilt.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
            self.ninja_azimuth.configure(state="disabled", fg_color=(THEME.border.gray, THEME.text.gray_dark))
        else:
            self.ninja_tilt.configure(state="normal", fg_color=(BG_INPUT_FOCUS, "#2B2B2B"))
            self.ninja_azimuth.configure(state="normal", fg_color=(BG_INPUT_FOCUS, "#2B2B2B"))

    def _build_pvgis_form(self):
        tabs_frame = customtkinter.CTkFrame(self.source_specific_frame, fg_color="transparent")
        tabs_frame.pack(fill="x", pady=(10, 10))
        
        self.hourly_tab_btn = customtkinter.CTkButton(
            tabs_frame, text="Hourly", width=100, height=28,
            command=lambda: self._set_pvgis_tab("HOURLY")
        )
        self.hourly_tab_btn.pack(side="left", padx=(0, 5))
        
        self.tmy_tab_btn = customtkinter.CTkButton(
            tabs_frame, text="TMY", width=100, height=28,
            command=lambda: self._set_pvgis_tab("TMY")
        )
        self.tmy_tab_btn.pack(side="left")
        
        self.pvgis_body_frame = customtkinter.CTkFrame(
            self.source_specific_frame, fg_color="transparent"
        )
        self.pvgis_body_frame.pack(fill="x")
        
        self._set_pvgis_tab(self.pvgis_mode_var.get())

    def _set_pvgis_tab(self, mode):
        self.pvgis_mode_var.set(mode)
        active_color = PRIMARY_BLUE
        active_text = "#FFFFFF"
        inactive_color = THEME.border.gray
        inactive_text = TEXT_SECONDARY
        
        if mode == "HOURLY":
            self.hourly_tab_btn.configure(fg_color=active_color, text_color=active_text, hover_color=THEME.primary.blue_deep)
            self.tmy_tab_btn.configure(fg_color=inactive_color, text_color=inactive_text, hover_color=THEME.border.medium)
            self._build_pvgis_hourly_form()
        else:
            self.tmy_tab_btn.configure(fg_color=active_color, text_color=active_text, hover_color=THEME.primary.blue_deep)
            self.hourly_tab_btn.configure(fg_color=inactive_color, text_color=inactive_text, hover_color=THEME.border.medium)
            self._build_pvgis_tmy_form()

    def _build_pvgis_hourly_form(self):
        for child in self.pvgis_body_frame.winfo_children():
            child.destroy()
        
        form_frame = customtkinter.CTkFrame(self.pvgis_body_frame, fg_color="transparent")
        form_frame.pack(fill="x")
        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        db_label = customtkinter.CTkLabel(
            form_frame, text="Solar radiation database *", 
            font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        db_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.pvgis_db_combo = customtkinter.CTkComboBox(
            form_frame, values=PVGIS_DATABASES, 
            width=COMBO_WIDTH, state="readonly",
            command=self._on_pvgis_database_change
        )
        self.pvgis_db_combo.set(DEFAULT_DATABASE_PVGIS)
        self.pvgis_db_combo.grid(row=row+1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        # Trigger initial discovery for default database
        self._fetch_and_update_pvgis_range(DEFAULT_DATABASE_PVGIS)
        
        sy_label = customtkinter.CTkLabel(
            form_frame, text="Start year *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        sy_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        ey_label = customtkinter.CTkLabel(
            form_frame, text="End year *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        ey_label.grid(row=row, column=1, sticky="w", padx=8, pady=(0, 4))
        
        self.pvgis_start_year = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{YEAR_MIN}-{YEAR_MAX}"
        )
        self.pvgis_start_year.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        
        self.pvgis_end_year = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{YEAR_MIN}-{YEAR_MAX}"
        )
        self.pvgis_end_year.grid(row=row+1, column=1, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        lat_label = customtkinter.CTkLabel(
            form_frame, text="Latitude (°) *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        lat_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        lon_label = customtkinter.CTkLabel(
            form_frame, text="Longitude (°) *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        lon_label.grid(row=row, column=1, sticky="w", padx=8, pady=(0, 4))
        
        self.pvgis_lat = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{LAT_MIN} to {LAT_MAX}"
        )
        self.pvgis_lat.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        
        self.pvgis_lon = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{LON_MIN} to {LON_MAX}"
        )
        self.pvgis_lon.grid(row=row+1, column=1, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        alt_label = customtkinter.CTkLabel(
            form_frame, text="Altitude (m)", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        alt_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.pvgis_alt = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text="Optional"
        )
        self.pvgis_alt.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        mount_label = customtkinter.CTkLabel(
            form_frame, text="Mounting type *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        mount_label.grid(row=row, column=0, sticky="w", padx=8, pady=(12, 4))
        
        mount_frame = customtkinter.CTkFrame(form_frame, fg_color="transparent")
        mount_frame.grid(row=row+1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))
        
        self.pvgis_mount_var = tkinter.StringVar(value=DEFAULT_MOUNTING)
        self.pvgis_mount_var.trace_add("write", self._on_pvgis_mounting_change)
        
        customtkinter.CTkRadioButton(
            mount_frame, text="Fixed", variable=self.pvgis_mount_var, 
            value="fixed", font=(FONT_FAMILY_TEXT, 12)
        ).pack(side="left", padx=(0, 15))
        customtkinter.CTkRadioButton(
            mount_frame, text="Vertical axis", variable=self.pvgis_mount_var,
            value="vertical_axis", font=(FONT_FAMILY_TEXT, 12)
        ).pack(side="left", padx=(0, 15))
        customtkinter.CTkRadioButton(
            mount_frame, text="Inclined axis", variable=self.pvgis_mount_var,
            value="inclined_axis", font=(FONT_FAMILY_TEXT, 12)
        ).pack(side="left", padx=(0, 15))
        customtkinter.CTkRadioButton(
            mount_frame, text="Two axis", variable=self.pvgis_mount_var,
            value="two_axis", font=(FONT_FAMILY_TEXT, 12)
        ).pack(side="left")
        row += 2
        
        self.pvgis_slope_label = customtkinter.CTkLabel(
            form_frame, text="Slope [°]", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        self.pvgis_slope_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        azim_label = customtkinter.CTkLabel(
            form_frame, text="Azimuth [°]", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        azim_label.grid(row=row, column=1, sticky="w", padx=8, pady=(0, 4))
        
        self.pvgis_slope = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{SLOPE_MIN}-{SLOPE_MAX}"
        )
        self.pvgis_slope.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        
        self.pvgis_azimuth = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{AZIMUTH_MIN} to {AZIMUTH_MAX}"
        )
        self.pvgis_azimuth.grid(row=row+1, column=1, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        opt_frame = customtkinter.CTkFrame(form_frame, fg_color="transparent")
        opt_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))
        
        self.pvgis_opt_slope_var = tkinter.BooleanVar(value=False)
        self.pvgis_opt_azimuth_var = tkinter.BooleanVar(value=False)
        
        self.opt_slope_cb = customtkinter.CTkCheckBox(
            opt_frame, text="Optimize tilt", variable=self.pvgis_opt_slope_var,
            font=(FONT_FAMILY_TEXT, 12),
            command=self._on_pvgis_optimize_change
        )
        self.opt_slope_cb.pack(side="left", padx=(0, 20))
        
        self.opt_azimuth_cb = customtkinter.CTkCheckBox(
            opt_frame, text="Optimize tilt and azimuth", variable=self.pvgis_opt_azimuth_var,
            font=(FONT_FAMILY_TEXT, 12),
            command=self._on_pvgis_optimize_change
        )
        self.opt_azimuth_cb.pack(side="left")
        row += 1
        self.pvgis_opt_hint_label = customtkinter.CTkLabel(
            form_frame,
            text="If neither is selected and no angles are entered, optimal angles are used.",
            font=(FONT_FAMILY_TEXT, 11), text_color=TEXT_MUTED,
        )
        self.pvgis_opt_hint_label.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))
        row += 1
        
        pv_header = customtkinter.CTkLabel(
            form_frame, text="PV power", font=(FONT_FAMILY_DISPLAY, 14, "bold"), text_color=TEXT_PRIMARY
        )
        pv_header.grid(row=row, column=0, sticky="w", padx=8, pady=(20, 8))
        row += 1
        
        tech_label = customtkinter.CTkLabel(
            form_frame, text="PV technology *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        tech_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.pvgis_tech_combo = customtkinter.CTkComboBox(
            form_frame, 
            values=PV_TECH_OPTIONS,
            width=COMBO_WIDTH, state="readonly"
        )
        self.pvgis_tech_combo.set(DEFAULT_PV_TECH)
        self.pvgis_tech_combo.grid(row=row+1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        power_label = customtkinter.CTkLabel(
            form_frame, text="Installed peak PV power [kWp] *", 
            font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        power_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        loss_label = customtkinter.CTkLabel(
            form_frame, text="System loss [%] *", 
            font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        loss_label.grid(row=row, column=1, sticky="w", padx=8, pady=(0, 4))
        
        self.pvgis_power = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text="> 0"
        )
        self.pvgis_power.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        
        self.pvgis_loss = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{LOSS_MIN}-{LOSS_MAX}"
        )
        self.pvgis_loss.grid(row=row+1, column=1, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        self.pvgis_rad_comp_var = tkinter.BooleanVar(value=False)
        customtkinter.CTkCheckBox(
            form_frame, text="Radiation components", variable=self.pvgis_rad_comp_var,
            font=(FONT_FAMILY_TEXT, 12)
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))

    def _build_pvgis_tmy_form(self):
        for child in self.pvgis_body_frame.winfo_children():
            child.destroy()
        
        form_frame = customtkinter.CTkFrame(self.pvgis_body_frame, fg_color="transparent")
        form_frame.pack(fill="x")
        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        lat_label = customtkinter.CTkLabel(
            form_frame, text="Latitude (°) *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        lat_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        lon_label = customtkinter.CTkLabel(
            form_frame, text="Longitude (°) *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        lon_label.grid(row=row, column=1, sticky="w", padx=8, pady=(0, 4))
        
        self.tmy_lat = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{LAT_MIN} to {LAT_MAX}"
        )
        self.tmy_lat.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        
        self.tmy_lon = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{LON_MIN} to {LON_MAX}"
        )
        self.tmy_lon.grid(row=row+1, column=1, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        database_label = customtkinter.CTkLabel(
            form_frame, text="Select database *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        database_label.grid(row=row, column=0, sticky="w", padx=8, pady=(8, 4))
        
        self.tmy_database_combo = customtkinter.CTkComboBox(
            form_frame, 
            values=TMY_DATABASES,
            width=COMBO_WIDTH, state="readonly"
        )
        self.tmy_database_combo.set(DEFAULT_DATABASE_TMY)
        self.tmy_database_combo.grid(row=row+1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))

    def _build_ninja_form(self):
        """Build Renewables Ninja PV form (PV + wind speed from MERRA-2)"""
        self.ninja_body_frame = customtkinter.CTkFrame(
            self.source_specific_frame, fg_color="transparent"
        )
        self.ninja_body_frame.pack(fill="x")
        self._build_ninja_pv_form()
    
    def _build_ninja_pv_form(self):
        """Build Renewables Ninja PV form (existing implementation)"""
        # Clear existing content
        for child in self.ninja_body_frame.winfo_children():
            child.destroy()
        
        form_frame = customtkinter.CTkFrame(self.ninja_body_frame, fg_color="transparent")
        form_frame.pack(fill="x")
        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        lat_label = customtkinter.CTkLabel(
            form_frame, text="Latitude (°) *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        lat_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        lon_label = customtkinter.CTkLabel(
            form_frame, text="Longitude (°) *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        lon_label.grid(row=row, column=1, sticky="w", padx=8, pady=(0, 4))
        
        self.ninja_lat = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text="e.g., 45.81"
        )
        self.ninja_lat.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        
        self.ninja_lon = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text="e.g., 15.98"
        )
        self.ninja_lon.grid(row=row+1, column=1, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        dataset_label = customtkinter.CTkLabel(
            form_frame, text="Dataset *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        dataset_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.ninja_dataset = customtkinter.CTkComboBox(
            form_frame, values=NINJA_DATASETS,
            width=COMBO_WIDTH, state="readonly",
            command=self._on_ninja_dataset_change
        )
        self.ninja_dataset.set(DEFAULT_DATASET_NINJA)
        self.ninja_dataset.grid(row=row+1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        # Trigger initial discovery for default dataset
        self._fetch_and_update_ninja_range(DEFAULT_DATASET_NINJA)
        
        year_label = customtkinter.CTkLabel(
            form_frame, text="Select a year of data *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        year_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.ninja_year = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text="1980-2023"
        )
        self.ninja_year.grid(row=row+1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        cap_label = customtkinter.CTkLabel(
            form_frame, text="Capacity [kW] *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        cap_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.ninja_capacity = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text="Maximum AC electrical power"
        )
        self.ninja_capacity.insert(0, "1")
        self.ninja_capacity.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        loss_label = customtkinter.CTkLabel(
            form_frame, text="System loss (%) *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        loss_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.ninja_loss = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text="0-100 (e.g., 14)"
        )
        self.ninja_loss.insert(0, "14")
        self.ninja_loss.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        pv_height_label = customtkinter.CTkLabel(
            form_frame, text="PV height [m] *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        pv_height_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.ninja_pv_height = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{WIND_HEIGHT_MIN}-{WIND_HEIGHT_MAX}"
        )
        self.ninja_pv_height.insert(0, "10")
        self.ninja_pv_height.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        track_label = customtkinter.CTkLabel(
            form_frame, text="Tracking *", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        track_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        self.ninja_tracking = customtkinter.CTkComboBox(
            form_frame, values=NINJA_TRACKING_OPTIONS,
            width=ENTRY_WIDTH, state="readonly"
        )
        self.ninja_tracking.set(DEFAULT_TRACKING)
        self.ninja_tracking.grid(row=row+1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        self.ninja_opt_angles_var = tkinter.BooleanVar(value=DEFAULT_OPTIMAL_ANGLES)
        self.ninja_opt_angles_cb = customtkinter.CTkCheckBox(
            form_frame, text="Use optimal tilt and azimuth", variable=self.ninja_opt_angles_var,
            font=(FONT_FAMILY_TEXT, 12),
            command=self._on_ninja_optimize_change
        )
        self.ninja_opt_angles_cb.grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))
        row += 1
        
        tilt_label = customtkinter.CTkLabel(
            form_frame, text="Tilt [°]", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        tilt_label.grid(row=row, column=0, sticky="w", padx=8, pady=(0, 4))
        
        azim_label = customtkinter.CTkLabel(
            form_frame, text="Azimuth [°]", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        azim_label.grid(row=row, column=1, sticky="w", padx=8, pady=(0, 4))
        
        self.ninja_tilt = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{SLOPE_MIN}-{SLOPE_MAX}"
        )
        self.ninja_tilt.grid(row=row+1, column=0, sticky="w", padx=8, pady=(0, 12))
        
        self.ninja_azimuth = customtkinter.CTkEntry(
            form_frame, width=ENTRY_WIDTH, placeholder_text=f"{AZIMUTH_MIN} to {AZIMUTH_MAX}"
        )
        self.ninja_azimuth.grid(row=row+1, column=1, sticky="w", padx=8, pady=(0, 12))
        row += 2
        
        self.ninja_raw_var = tkinter.BooleanVar(value=False)
        customtkinter.CTkCheckBox(
            form_frame, text="Include raw data", variable=self.ninja_raw_var,
            font=(FONT_FAMILY_TEXT, 12)
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(12, 0))
        
        # Restore cached values if available
        self._restore_ninja_pv_cache()
        
        self._on_ninja_optimize_change()
    
    def _on_import_data(self):
        source = self.src_combo.get()
        try:
            if source == "PVGIS":
                self._import_pvgis()
            else:
                self._import_ninja()
        except Exception as e:
            self.step1_completed = False
            self._cached_hourly_df = None
            self._cached_monthly_df = None
            self._cached_yearly_df = None
            self._view_data_prepared = False
            self.status_label.configure(text=f"Error: {str(e)}", text_color=ERROR_RED)
            self.import_button.configure(state="normal", text="Import data")
            self._update_next_button_state()


    def _start_progress(self):
        if hasattr(self, "progress_bar") and not self.progress_bar.winfo_exists():
            del self.progress_bar
        if not hasattr(self, "progress_bar"):
            self.progress_bar = customtkinter.CTkProgressBar(self.status_label.master, mode="indeterminate", height=4)
        
        # Always pack it when starting, just in case it was pack_forget() previously
        try:
            self.progress_bar.pack(side="bottom", fill="x", pady=(10, 0), padx=8, before=self.status_label)
        except Exception:
            pass # Already packed or error packing
            
        self.progress_bar.set(0)
        self.progress_bar.start()

    def _stop_progress(self):
        if hasattr(self, "progress_bar") and self.progress_bar.winfo_exists():
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            
    def _reset_cache(self):
        self._cached_hourly_df = None
        self._cached_monthly_df = None
        self._cached_yearly_df = None
        self._view_data_prepared = False
        self.import_button.configure(state="normal", text="Import data")
        self._update_next_button_state()
        
    def _handle_import_error(self, e):
        self.step1_completed = False
        self._reset_cache()
        self.status_label.configure(text=f"Error: {str(e)}", text_color=ERROR_RED)

    def _import_pvgis(self):
        """Handle PVGIS import validation with REAL API calls"""
        mode = self.pvgis_mode_var.get()
        
        try:
            if mode == "HOURLY":
                database = self.pvgis_db_combo.get()
                if not database:
                    raise ValueError("Solar radiation database is required")
                
                start_year_str = self.pvgis_start_year.get().strip()
                end_year_str = self.pvgis_end_year.get().strip()
                
                if not start_year_str or not end_year_str:
                    raise ValueError("Start and end years are required")
                    
                start_year = int(start_year_str)
                end_year = int(end_year_str)
                
                # Use discovered year range if available, fallback to defaults
                year_min = getattr(self, '_current_pvgis_year_min', YEAR_MIN)
                year_max = getattr(self, '_current_pvgis_year_max', YEAR_MAX)
                
                if not (year_min <= start_year <= year_max and year_min <= end_year <= year_max):
                    raise ValueError(f"Years must be between {year_min} and {year_max}")
                if start_year > end_year:
                    raise ValueError("Start year must be <= End year")
                
                lat = float(self.pvgis_lat.get())
                lon = float(self.pvgis_lon.get())
                if not (LAT_MIN <= lat <= LAT_MAX):
                    raise ValueError(f"Latitude must be between {LAT_MIN} and {LAT_MAX}")
                if not (LON_MIN <= lon <= LON_MAX):
                    raise ValueError(f"Longitude must be between {LON_MIN} and {LON_MAX}")
                
                alt = None
                if self.pvgis_alt.get().strip():
                    alt = float(self.pvgis_alt.get())
                
                mounting = self.pvgis_mount_var.get()
                
                slope_placeholder = f"{SLOPE_MIN}-{SLOPE_MAX}"
                azimuth_placeholder = f"{AZIMUTH_MIN} to {AZIMUTH_MAX}"
                slope_raw = self.pvgis_slope.get().strip()
                azimuth_raw = self.pvgis_azimuth.get().strip()
                if slope_raw and slope_raw != slope_placeholder:
                    slope = float(slope_raw)
                    if not (SLOPE_MIN <= slope <= SLOPE_MAX):
                        raise ValueError(f"Slope must be {SLOPE_MIN}-{SLOPE_MAX}")
                else:
                    slope = None
                if azimuth_raw and azimuth_raw != azimuth_placeholder:
                    azimuth = float(azimuth_raw)
                    if not (AZIMUTH_MIN <= azimuth <= AZIMUTH_MAX):
                        raise ValueError(f"Azimuth must be {AZIMUTH_MIN} to {AZIMUTH_MAX}")
                else:
                    azimuth = None
                
                tech = self.pvgis_tech_combo.get()
                if not tech:
                    raise ValueError("PV technology is required")
                
                power = float(self.pvgis_power.get())
                if power <= 0:
                    raise ValueError("Peak power must be > 0")
                
                loss = float(self.pvgis_loss.get())
                if not (LOSS_MIN <= loss <= LOSS_MAX):
                    raise ValueError(f"System loss must be {LOSS_MIN}-{LOSS_MAX}%")
                
                optimize_slope = self.pvgis_opt_slope_var.get()
                optimize_azimuth = self.pvgis_opt_azimuth_var.get()
                
                if mounting in ("inclined_axis", "two_axis"):
                    slope = None
                    azimuth = None
                
                self.import_button.configure(state="disabled", text="Importing...")
                self.status_label.configure(
                    text="Fetching data from PVGIS API...\n(This may take 10-30 seconds)",
                    text_color=PRIMARY_BLUE
                )
                self.update()
                
                
                from source.pvgis_client import fetch_pvgis_hourly
                
                self._start_progress()
                def t_job():
                    try:
                        result = fetch_pvgis_hourly(
                            latitude=lat, longitude=lon, start_year=start_year,
                            end_year=end_year, peak_power_kwp=power,
                            system_loss_percent=loss, mounting_type=mounting,
                            slope=slope, azimuth=azimuth, database=database,
                            optimize_slope=optimize_slope, optimize_slope_azimuth=optimize_azimuth,
                            altitude=alt, pv_technology=tech,
                            include_components=self.pvgis_rad_comp_var.get()
                        )
                        self.after(0, _on_success, result)
                    except Exception as e:
                        self.after(0, self._handle_import_error, e)
                        self.after(0, self._stop_progress)

                def _on_success(result):
                    self.import_config = {
                        "source": "PVGIS", "pvgis_mode": "HOURLY", "database": database,
                        "start_year": start_year, "end_year": end_year, "latitude": lat,
                        "longitude": lon, "altitude": alt, "mounting_type": mounting,
                        "slope": slope, "azimuth": azimuth, "optimize_slope": optimize_slope,
                        "optimize_slope_azimuth": optimize_azimuth, "pv_technology": tech,
                        "peak_power_kwp": power, "system_loss_percent": loss,
                        "radiation_components": self.pvgis_rad_comp_var.get(),
                        "api_result": result
                    }
                    num_records = len(result["hourly_data"])
                    annual_kwh = result["annual_total_kwh"]
                    self.status_label.configure(
                        text=f"OK Import successful: {fmt_num(num_records)} hourly records\nTotal annual: {fmt_num(annual_kwh, 0)} kWh",
                        text_color=SUCCESS_GREEN
                    )
                    self.step1_completed = True
                    self.app.source_config_cache['import_success'] = True
                    self._update_step_visuals()
                    self._reset_cache()
                    self._stop_progress()
                    
                threading.Thread(target=t_job, daemon=True).start()
                return # Skip reset cache at the bottom
                
            else:  # TMY mode
                lat = float(self.tmy_lat.get())
                lon = float(self.tmy_lon.get())
                if not (LAT_MIN <= lat <= LAT_MAX):
                    raise ValueError(f"Latitude must be between {LAT_MIN} and {LAT_MAX}")
                if not (LON_MIN <= lon <= LON_MAX):
                    raise ValueError(f"Longitude must be between {LON_MIN} and {LON_MAX}")
                
                database = self.tmy_database_combo.get()
                if not database:
                    raise ValueError("Please select a database")
                
                self.import_button.configure(state="disabled", text="Importing...")
                self.status_label.configure(
                    text="Fetching TMY data from PVGIS...",
                    text_color=PRIMARY_BLUE
                )
                self.update()
                
                
                from source.pvgis_client import fetch_pvgis_tmy
                self._start_progress()
                def t_job():
                    try:
                        result = fetch_pvgis_tmy(latitude=lat, longitude=lon, database=database)
                        self.after(0, _on_success, result)
                    except Exception as e:
                        self.after(0, self._handle_import_error, e)
                        self.after(0, self._stop_progress)
                def _on_success(result):
                    self.import_config = {
                        "source": "PVGIS", "pvgis_mode": "TMY", "latitude": lat, "longitude": lon,
                        "tmy_database": database, "api_result": result
                    }
                    num_records = len(result.get("hourly_data", []))
                    self.status_label.configure(
                        text=f"OK TMY Import successful: {fmt_num(num_records)} hourly records",
                        text_color=SUCCESS_GREEN
                    )
                    self.step1_completed = True
                    self.app.source_config_cache['import_success'] = True
                    self._update_step_visuals()
                    self._reset_cache()
                    self._stop_progress()
                    
                threading.Thread(target=t_job, daemon=True).start()
                return
            
            self._cached_hourly_df = None
            self._cached_monthly_df = None
            self._cached_yearly_df = None
            self._view_data_prepared = False
            
            self.import_button.configure(state="normal", text="Import data")
            self._update_next_button_state()
            
        except ValueError as e:
            self.step1_completed = False
            self._cached_hourly_df = None
            self._cached_monthly_df = None
            self._cached_yearly_df = None
            self._view_data_prepared = False
            self.status_label.configure(text=f"Validation Error: {str(e)}", text_color=ERROR_RED)
            self.import_button.configure(state="normal", text="Import data")
            self._update_next_button_state()
        except Exception as e:
            self.step1_completed = False
            self._cached_hourly_df = None
            self._cached_monthly_df = None
            self._cached_yearly_df = None
            self._view_data_prepared = False
            self.status_label.configure(text=f"Error: {str(e)}", text_color=ERROR_RED)
            self.import_button.configure(state="normal", text="Import data")
            self._update_next_button_state()

    def _import_ninja(self):
        """Handle Renewables Ninja PV import (PV data + wind speed from MERRA-2)"""
        self._import_ninja_pv()
    
    def _import_ninja_pv(self):
        """Handle Renewables Ninja PV import"""
        try:
            from source.ninja_client import DEFAULT_NINJA_TOKEN
            token = DEFAULT_NINJA_TOKEN
            
            lat_str = self.ninja_lat.get().strip()
            lon_str = self.ninja_lon.get().strip()
            dataset_label = self.ninja_dataset.get().strip()
            year_str = self.ninja_year.get().strip()
            capacity_str = self.ninja_capacity.get().strip()
            loss_str = self.ninja_loss.get().strip()
            tracking_label = self.ninja_tracking.get().strip()
            tilt_str = self.ninja_tilt.get().strip()
            azimuth_str = self.ninja_azimuth.get().strip()
            include_raw = self.ninja_raw_var.get()
            pv_height_str = self.ninja_pv_height.get().strip()
            
            if not lat_str or not lon_str:
                raise ValueError("Latitude and longitude are required")
            
            lat = float(lat_str)
            lon = float(lon_str)
            
            if not (LAT_MIN <= lat <= LAT_MAX):
                raise ValueError(f"Latitude must be between {LAT_MIN} and {LAT_MAX}")
            if not (LON_MIN <= lon <= LON_MAX):
                raise ValueError(f"Longitude must be between {LON_MIN} and {LON_MAX}")
            
            if not year_str:
                raise ValueError("Year is required")
            year = int(year_str)
            
            # Use discovered year range if available, fallback to defaults
            year_min = getattr(self, '_current_ninja_year_min', YEAR_MIN)
            year_max = getattr(self, '_current_ninja_year_max', 2023)
            
            if not (year_min <= year <= year_max):
                raise ValueError(f"Year must be between {year_min} and {year_max}")
            
            if not capacity_str:
                raise ValueError("Capacity is required")
            capacity = float(capacity_str)
            if capacity <= 0:
                raise ValueError("Capacity must be greater than 0")
            
            if not loss_str:
                raise ValueError("System loss is required")
            loss_percent = float(loss_str)
            if not (0 <= loss_percent <= 100):
                raise ValueError("System loss must be between 0 and 100 percent")
            loss = loss_percent / 100.0
            
            if not pv_height_str:
                raise ValueError("PV height is required (for wind speed fetch)")
            pv_height = float(pv_height_str)
            if not (WIND_HEIGHT_MIN <= pv_height <= WIND_HEIGHT_MAX):
                raise ValueError(f"PV height must be between {WIND_HEIGHT_MIN} and {WIND_HEIGHT_MAX} meters")
            
            use_optimal = self.ninja_opt_angles_var.get()
            if use_optimal:
                tilt = abs(lat)
                azimuth = 0
                self.ninja_tilt.delete(0, 'end')
                self.ninja_tilt.insert(0, str(round(tilt, 1)))
                self.ninja_azimuth.delete(0, 'end')
                self.ninja_azimuth.insert(0, str(azimuth))
            else:
                if not tilt_str:
                    raise ValueError("Tilt is required when not using optimal angles")
                tilt = float(tilt_str)
                if not (SLOPE_MIN <= tilt <= SLOPE_MAX):
                    raise ValueError(f"Tilt must be between {SLOPE_MIN} and {SLOPE_MAX}")
                
                if not azimuth_str:
                    raise ValueError("Azimuth is required when not using optimal angles")
                azimuth = float(azimuth_str)
                if not (AZIMUTH_MIN <= azimuth <= AZIMUTH_MAX):
                    raise ValueError(f"Azimuth must be between {AZIMUTH_MIN} and {AZIMUTH_MAX}")
            
            if not tracking_label:
                raise ValueError("Tracking mode is required")
            
            self.import_button.configure(state="disabled", text="Importing...")
            self.status_label.configure(
                text="Fetching PV and wind speed from Renewables.ninja...\n(This may take 15-45 seconds)",
                text_color=PRIMARY_BLUE
            )
            self.update()
            
            from source.ninja_client import fetch_ninja_pv, fetch_ninja_wind_speed
            
            self._start_progress()
            def t_job():
                try:
                    result = fetch_ninja_pv(
                        latitude=lat, longitude=lon, year=year,
                        dataset=dataset_label, capacity_kw=capacity,
                        system_loss_fraction=loss, tracking_mode=tracking_label,
                        tilt_deg=tilt, azimuth_deg=azimuth, include_raw=include_raw, token=token
                    )
                    
                    try:
                        hourly_df = result["hourly_data"].copy()
                        wind_series = fetch_ninja_wind_speed(
                            latitude=lat, longitude=lon, year=year,
                            hub_height_m=pv_height, capacity_kw=capacity,
                            turbine_model=DEFAULT_WIND_TURBINE, token=token
                        )
                        if wind_series is not None:
                            time_col = next((c for c in hourly_df.columns if "time" in str(c).lower()), None)
                            if time_col is not None:
                                pv_times = pd.to_datetime(hourly_df[time_col], utc=True)
                                aligned = wind_series.reindex(pv_times)
                                vals = aligned.values
                                if len(vals) == len(hourly_df) and pd.isna(vals).all():
                                    vals = wind_series.values
                                hourly_df["wind_speed"] = vals
                        result["hourly_data"] = hourly_df
                    except Exception as e:
                        print(f"Wind speed fetch failed (PV data OK): {e}")

                    self.after(0, _on_success, result)
                except Exception as e:
                    self.after(0, self._handle_import_error, e)
                    self.after(0, self._stop_progress)

            def _on_success(result):
                self.import_config = {
                    "source": "NINJA", "ninja_mode": "PV", "latitude": lat, "longitude": lon,
                    "pv_height_m": pv_height, "dataset": dataset_label, "year": year,
                    "capacity_kw": capacity, "system_loss_fraction": loss,
                    "tracking": tracking_label, "tilt": tilt, "azimuth": azimuth,
                    "use_optimal_angles": use_optimal, "include_raw": include_raw, "api_result": result
                }
                num_records = len(result["hourly_data"])
                annual_kwh = result["annual_total_kwh"]
                self.status_label.configure(
                    text=f"OK Import successful: {fmt_num(num_records)} hourly records\nTotal annual: {fmt_num(annual_kwh, 0)} kWh",
                    text_color=SUCCESS_GREEN
                )
                self.step1_completed = True
                self.app.source_config_cache['import_success'] = True
                self._update_step_visuals()
                self._reset_cache()
                self._stop_progress()

            threading.Thread(target=t_job, daemon=True).start()
            return
            
        except ValueError as e:
            self.step1_completed = False
            self._cached_hourly_df = None
            self._cached_monthly_df = None
            self._cached_yearly_df = None
            self._view_data_prepared = False
            self.status_label.configure(text=f"Validation Error: {str(e)}", text_color=ERROR_RED)
            self.import_button.configure(state="normal", text="Import data")
            self._update_next_button_state()
        except Exception as e:
            self.step1_completed = False
            self._cached_hourly_df = None
            self._cached_monthly_df = None
            self._cached_yearly_df = None
            self._view_data_prepared = False
            self.status_label.configure(text=f"Error: {str(e)}", text_color=ERROR_RED)
            self.import_button.configure(state="normal", text="Import data")
            self._update_next_button_state()
    
    # ============================================
    # API METADATA DISCOVERY METHODS
    # ============================================
    
    def _on_pvgis_database_change(self, choice):
        """Handle PVGIS database change - trigger year range discovery"""
        self._fetch_and_update_pvgis_range(choice)
    
    def _on_ninja_dataset_change(self, choice):
        """Handle Ninja dataset change - trigger year range discovery"""
        self._fetch_and_update_ninja_range(choice)
    
    def _fetch_and_update_pvgis_range(self, database):
        """Fetch year range for PVGIS and update UI"""
        def fetch_in_background():
            range_data = metadata_discovery.get_range_for_dataset("pvgis", database)
            year_min = range_data["min"]
            year_max = range_data["max"]
            source_note = " live" if range_data["source"] == "api_probe" else " cached"
            
            # Update UI from main thread
            self.after(0, lambda: self._update_pvgis_year_placeholders(year_min, year_max, source_note))
            
        
        # Run in background thread
        thread = threading.Thread(target=fetch_in_background, daemon=True)
        thread.start()
    
    def _fetch_and_update_ninja_range(self, dataset):
        """Fetch year range for Ninja and update UI"""
        def fetch_in_background():
            range_data = metadata_discovery.get_range_for_dataset("ninja", dataset)
            year_min = range_data["min"]
            year_max = range_data["max"]
            source_note = " live" if range_data["source"] == "api_probe" else " cached"
            
            # Update UI from main thread
            self.after(0, lambda: self._update_ninja_year_placeholders(year_min, year_max, source_note))
            
        
        # Run in background thread
        thread = threading.Thread(target=fetch_in_background, daemon=True)
        thread.start()
    
    def _update_pvgis_year_placeholders(self, year_min, year_max, source_note):
        """Update PVGIS year entry placeholders"""
        if hasattr(self, 'pvgis_start_year') and self.pvgis_start_year.winfo_exists():
            self.pvgis_start_year.configure(placeholder_text=f"{year_min}-{year_max}{source_note}")
        if hasattr(self, 'pvgis_end_year') and self.pvgis_end_year.winfo_exists():
            self.pvgis_end_year.configure(placeholder_text=f"{year_min}-{year_max}{source_note}")
        
        # Store current range for validation
        self._current_pvgis_year_min = year_min
        self._current_pvgis_year_max = year_max
        
        # Update status if needed
        if hasattr(self, 'status_label'):
            self.status_label.configure(
                text=f"Data available: {year_min}-{year_max}",
                text_color=PRIMARY_BLUE if "live" in source_note else TEXT_SECONDARY
            )
    
    def _update_ninja_year_placeholders(self, year_min, year_max, source_note):
        """Update Ninja year entry placeholders"""
        if hasattr(self, 'ninja_year') and self.ninja_year.winfo_exists():
            self.ninja_year.configure(placeholder_text=f"{year_min}-{year_max}{source_note}")
        
        # Store current range for validation
        self._current_ninja_year_min = year_min
        self._current_ninja_year_max = year_max
        
        # Update status if needed
        if hasattr(self, 'status_label'):
            self.status_label.configure(
                text=f"Data available: {year_min}-{year_max}",
                text_color=PRIMARY_BLUE if "live" in source_note else TEXT_SECONDARY
            )
    
    def refresh_all_api_metadata(self):
        """
        Force refresh all API metadata on app startup
        Call this from main app initialization
        """
        def fetch_all_in_background():
            
            # PVGIS databases
            for db in ["PVGIS-ERA5", "PVGIS-SARAH3"]:
                metadata_discovery.discover_pvgis_range(db)
            
            # Ninja datasets
            for dataset in ["CM-SAF SARAH (Europe)", "MERRA-2 (global)"]:
                metadata_discovery.discover_ninja_range(dataset)
            
        
        thread = threading.Thread(target=fetch_all_in_background, daemon=True)
        thread.start()
    
    def _safe_cache_get(self, getter, default=''):
        """Get value from a widget or getter; return default if widget was destroyed (e.g. tab switch)."""
        try:
            return getter()
        except Exception:
            return default

    def _cache_step1_inputs(self):
        """Cache all Step 1 input values before navigating to Step 2"""
        # Use safe getters: TMY/Ninja widgets may be destroyed when another tab (e.g. PVGIS Hourly) is active
        cached = {
            # Data source
            'source': self._safe_cache_get(lambda: self.src_combo.get(), 'PVGIS'),
            # PVGIS mode
            'pvgis_mode': self._safe_cache_get(lambda: self.pvgis_mode_var.get(), 'HOURLY'),
            # Ninja mode
            # PVGIS Hourly fields
            'pvgis_db': self._safe_cache_get(lambda: self.pvgis_db_combo.get(), ''),
            'pvgis_start_year': self._safe_cache_get(lambda: self.pvgis_start_year.get(), ''),
            'pvgis_end_year': self._safe_cache_get(lambda: self.pvgis_end_year.get(), ''),
            'pvgis_lat': self._safe_cache_get(lambda: self.pvgis_lat.get(), ''),
            'pvgis_lon': self._safe_cache_get(lambda: self.pvgis_lon.get(), ''),
            'pvgis_alt': self._safe_cache_get(lambda: self.pvgis_alt.get(), ''),
            'pvgis_mount': self._safe_cache_get(lambda: self.pvgis_mount_var.get(), 'fixed'),
            'pvgis_slope': self._safe_cache_get(lambda: self.pvgis_slope.get(), ''),
            'pvgis_azimuth': self._safe_cache_get(lambda: self.pvgis_azimuth.get(), ''),
            'pvgis_opt_slope': self._safe_cache_get(lambda: self.pvgis_opt_slope_var.get(), False),
            'pvgis_opt_azimuth': self._safe_cache_get(lambda: self.pvgis_opt_azimuth_var.get(), False),
            'pvgis_tech': self._safe_cache_get(lambda: self.pvgis_tech_combo.get(), ''),
            'pvgis_power': self._safe_cache_get(lambda: self.pvgis_power.get(), ''),
            'pvgis_loss': self._safe_cache_get(lambda: self.pvgis_loss.get(), ''),
            'pvgis_rad_comp': self._safe_cache_get(lambda: self.pvgis_rad_comp_var.get(), False),
            # PVGIS TMY fields (widgets destroyed when Hourly tab is active)
            'tmy_lat': self._safe_cache_get(lambda: self.tmy_lat.get(), ''),
            'tmy_lon': self._safe_cache_get(lambda: self.tmy_lon.get(), ''),
            'tmy_db': self._safe_cache_get(lambda: self.tmy_database_combo.get(), ''),
            # Ninja PV fields (widgets destroyed when WIND tab is active)
            'ninja_lat': self._safe_cache_get(lambda: self.ninja_lat.get(), ''),
            'ninja_lon': self._safe_cache_get(lambda: self.ninja_lon.get(), ''),
            'ninja_dataset': self._safe_cache_get(lambda: self.ninja_dataset.get(), ''),
            'ninja_year': self._safe_cache_get(lambda: self.ninja_year.get(), ''),
            'ninja_capacity': self._safe_cache_get(lambda: self.ninja_capacity.get(), ''),
            'ninja_pv_height': self._safe_cache_get(lambda: self.ninja_pv_height.get(), ''),
            'ninja_loss': self._safe_cache_get(lambda: self.ninja_loss.get(), ''),
            'ninja_tracking': self._safe_cache_get(lambda: self.ninja_tracking.get(), ''),
            'ninja_opt_angles': self._safe_cache_get(lambda: self.ninja_opt_angles_var.get(), False),
            'ninja_tilt': self._safe_cache_get(lambda: self.ninja_tilt.get(), ''),
            'ninja_azimuth': self._safe_cache_get(lambda: self.ninja_azimuth.get(), ''),
            'ninja_raw': self._safe_cache_get(lambda: self.ninja_raw_var.get(), False),
        }
        
        self.app.source_config_cache['step1_inputs'] = cached
    
    def _restore_step1_inputs(self):
        """Restore Step 1 input values from cache when returning to Step 1"""
        cached = self.app.source_config_cache.get('step1_inputs', {})
        if not cached:
            return  # No cache yet

        self._is_restoring = True
        try:
            self._restore_step1_inputs_impl(cached)
        finally:
            self._is_restoring = False

    def _restore_step1_inputs_impl(self, cached):
        """Inner restore logic; _is_restoring guard prevents _on_source_change from overwriting cache."""
        cached_source = cached.get('source', 'PVGIS')

        # Restore PVGIS mode
        if cached.get('pvgis_mode') and hasattr(self, 'pvgis_mode_var'):
            self.pvgis_mode_var.set(cached['pvgis_mode'])
        
        # Restore data source and rebuild form to match
        if cached_source and hasattr(self, 'src_combo'):
            self.src_combo.set(cached_source)
            # Rebuild the form to match the cached source
            # Clear and rebuild source-specific frame
            for child in self.source_specific_frame.winfo_children():
                child.destroy()
            if cached_source == 'PVGIS':
                self._build_pvgis_form()
            else:
                self._build_ninja_form()
        
        # Restore PVGIS Hourly fields (widgets may not exist if TMY tab is active)
        # Use 'key in cached' to restore empty/zero values; avoid truthy-only checks
        try:
            if 'pvgis_db' in cached and hasattr(self, 'pvgis_db_combo'):
                val = cached.get('pvgis_db') or DEFAULT_DATABASE_PVGIS
                self.pvgis_db_combo.set(val)
            if 'pvgis_start_year' in cached and hasattr(self, 'pvgis_start_year'):
                self.pvgis_start_year.delete(0, 'end')
                self.pvgis_start_year.insert(0, str(cached.get('pvgis_start_year', '')))
            if 'pvgis_end_year' in cached and hasattr(self, 'pvgis_end_year'):
                self.pvgis_end_year.delete(0, 'end')
                self.pvgis_end_year.insert(0, str(cached.get('pvgis_end_year', '')))
            if 'pvgis_lat' in cached and hasattr(self, 'pvgis_lat'):
                self.pvgis_lat.delete(0, 'end')
                self.pvgis_lat.insert(0, str(cached.get('pvgis_lat', '')))
            if 'pvgis_lon' in cached and hasattr(self, 'pvgis_lon'):
                self.pvgis_lon.delete(0, 'end')
                self.pvgis_lon.insert(0, str(cached.get('pvgis_lon', '')))
            if 'pvgis_alt' in cached and hasattr(self, 'pvgis_alt'):
                self.pvgis_alt.delete(0, 'end')
                self.pvgis_alt.insert(0, str(cached.get('pvgis_alt', '')))
            if 'pvgis_mount' in cached and hasattr(self, 'pvgis_mount_var'):
                self.pvgis_mount_var.set(cached.get('pvgis_mount', 'fixed'))
            if 'pvgis_slope' in cached and hasattr(self, 'pvgis_slope'):
                self.pvgis_slope.delete(0, 'end')
                self.pvgis_slope.insert(0, str(cached.get('pvgis_slope', '')))
            if 'pvgis_azimuth' in cached and hasattr(self, 'pvgis_azimuth'):
                self.pvgis_azimuth.delete(0, 'end')
                self.pvgis_azimuth.insert(0, str(cached.get('pvgis_azimuth', '')))
            if 'pvgis_opt_slope' in cached and hasattr(self, 'pvgis_opt_slope_var'):
                self.pvgis_opt_slope_var.set(cached['pvgis_opt_slope'])
            if 'pvgis_opt_azimuth' in cached and hasattr(self, 'pvgis_opt_azimuth_var'):
                self.pvgis_opt_azimuth_var.set(cached['pvgis_opt_azimuth'])
            if 'pvgis_tech' in cached and hasattr(self, 'pvgis_tech_combo'):
                val = cached.get('pvgis_tech') or DEFAULT_PV_TECH
                self.pvgis_tech_combo.set(val)
            if 'pvgis_power' in cached and hasattr(self, 'pvgis_power'):
                self.pvgis_power.delete(0, 'end')
                self.pvgis_power.insert(0, str(cached.get('pvgis_power', '')))
            if 'pvgis_loss' in cached and hasattr(self, 'pvgis_loss'):
                self.pvgis_loss.delete(0, 'end')
                self.pvgis_loss.insert(0, str(cached.get('pvgis_loss', '')))
            if 'pvgis_rad_comp' in cached and hasattr(self, 'pvgis_rad_comp_var'):
                self.pvgis_rad_comp_var.set(cached['pvgis_rad_comp'])
        except Exception:
            pass
        
        # Restore PVGIS TMY fields (widgets may not exist if Hourly tab is active)
        try:
            if 'tmy_lat' in cached and hasattr(self, 'tmy_lat'):
                self.tmy_lat.delete(0, 'end')
                self.tmy_lat.insert(0, str(cached.get('tmy_lat', '')))
            if 'tmy_lon' in cached and hasattr(self, 'tmy_lon'):
                self.tmy_lon.delete(0, 'end')
                self.tmy_lon.insert(0, str(cached.get('tmy_lon', '')))
            if 'tmy_db' in cached and hasattr(self, 'tmy_database_combo'):
                val = cached.get('tmy_db') or DEFAULT_DATABASE_TMY
                self.tmy_database_combo.set(val)
        except Exception:
            pass

        # Restore Ninja PV fields
        try:
            if 'ninja_lat' in cached and hasattr(self, 'ninja_lat'):
                self.ninja_lat.delete(0, 'end')
                self.ninja_lat.insert(0, str(cached.get('ninja_lat', '')))
            if 'ninja_lon' in cached and hasattr(self, 'ninja_lon'):
                self.ninja_lon.delete(0, 'end')
                self.ninja_lon.insert(0, str(cached.get('ninja_lon', '')))
            if 'ninja_dataset' in cached and hasattr(self, 'ninja_dataset'):
                val = cached.get('ninja_dataset') or (self.import_config or {}).get('dataset') or DEFAULT_DATASET_NINJA
                if val in NINJA_DATASETS:
                    self.ninja_dataset.set(val)
                    self._fetch_and_update_ninja_range(val)
            if 'ninja_year' in cached and hasattr(self, 'ninja_year'):
                self.ninja_year.delete(0, 'end')
                self.ninja_year.insert(0, str(cached.get('ninja_year', '')))
            if 'ninja_capacity' in cached and hasattr(self, 'ninja_capacity'):
                self.ninja_capacity.delete(0, 'end')
                self.ninja_capacity.insert(0, str(cached.get('ninja_capacity', '')))
            if 'ninja_loss' in cached and hasattr(self, 'ninja_loss'):
                self.ninja_loss.delete(0, 'end')
                self.ninja_loss.insert(0, str(cached.get('ninja_loss', '')))
            if 'ninja_tracking' in cached and hasattr(self, 'ninja_tracking'):
                val = cached.get('ninja_tracking') or DEFAULT_TRACKING
                self.ninja_tracking.set(val)
            if 'ninja_opt_angles' in cached and hasattr(self, 'ninja_opt_angles_var'):
                self.ninja_opt_angles_var.set(cached['ninja_opt_angles'])
            if 'ninja_tilt' in cached and hasattr(self, 'ninja_tilt'):
                self.ninja_tilt.delete(0, 'end')
                self.ninja_tilt.insert(0, str(cached.get('ninja_tilt', '')))
            if 'ninja_azimuth' in cached and hasattr(self, 'ninja_azimuth'):
                self.ninja_azimuth.delete(0, 'end')
                self.ninja_azimuth.insert(0, str(cached.get('ninja_azimuth', '')))
            if 'ninja_raw' in cached and hasattr(self, 'ninja_raw_var'):
                self.ninja_raw_var.set(cached['ninja_raw'])
        except Exception:
            pass
        
        # Update UI states based on restored values
        self._update_ui_states_from_cache()
        
        # Re-apply import success state (may have been reset by src_combo command during restore)
        if self.import_config and self.import_config.get("api_result"):
            self.step1_completed = True
            self.app.source_config_cache['import_success'] = True
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                api_result = self.import_config.get("api_result", {})
                hourly = api_result.get("hourly_data")
                num_records = len(hourly) if hourly is not None else 0
                annual = api_result.get("annual_total_kwh", 0)
                self.status_label.configure(
                    text=f"OK Import successful: {fmt_num(num_records)} hourly records" + (
                        f"\nTotal annual: {fmt_num(annual, 0)} kWh" if annual else ""
                    ),
                    text_color=SUCCESS_GREEN
                )
            self._update_next_button_state()
    
    def _update_ui_states_from_cache(self):
        """Update UI enable/disable states to match restored values"""
        cached = self.app.source_config_cache.get('step1_inputs', {})
        cached_source = cached.get('source', 'PVGIS')

        # Only update PVGIS states when PVGIS form is displayed
        if cached_source == 'PVGIS':
            if hasattr(self, 'pvgis_mount_var'):
                self._on_pvgis_mounting_change()
            if hasattr(self, 'pvgis_opt_slope_var') or hasattr(self, 'pvgis_opt_azimuth_var'):
                self._on_pvgis_optimize_change()

        # Only update Ninja states when Ninja form is displayed
        if cached_source == 'Renewables Ninja':
            if hasattr(self, 'ninja_opt_angles_var'):
                self._on_ninja_optimize_change()
    
    def _restore_ninja_pv_cache(self):
        """Restore cached values to Ninja PV form"""
        cached = self.app.source_config_cache.get('step1_inputs', {})
        if not cached:
            return
        
        try:
            if 'ninja_lat' in cached and hasattr(self, 'ninja_lat'):
                self.ninja_lat.delete(0, 'end')
                self.ninja_lat.insert(0, str(cached.get('ninja_lat', '')))
            if 'ninja_lon' in cached and hasattr(self, 'ninja_lon'):
                self.ninja_lon.delete(0, 'end')
                self.ninja_lon.insert(0, str(cached.get('ninja_lon', '')))
            if 'ninja_dataset' in cached and hasattr(self, 'ninja_dataset'):
                val = cached.get('ninja_dataset') or (self.import_config or {}).get('dataset') or DEFAULT_DATASET_NINJA
                if val in NINJA_DATASETS:
                    self.ninja_dataset.set(val)
                    self._fetch_and_update_ninja_range(val)
            if 'ninja_year' in cached and hasattr(self, 'ninja_year'):
                self.ninja_year.delete(0, 'end')
                self.ninja_year.insert(0, str(cached.get('ninja_year', '')))
            if 'ninja_capacity' in cached and hasattr(self, 'ninja_capacity'):
                self.ninja_capacity.delete(0, 'end')
                self.ninja_capacity.insert(0, str(cached.get('ninja_capacity') if cached.get('ninja_capacity') else '1'))
            if 'ninja_pv_height' in cached and hasattr(self, 'ninja_pv_height'):
                self.ninja_pv_height.delete(0, 'end')
                self.ninja_pv_height.insert(0, str(cached.get('ninja_pv_height') if cached.get('ninja_pv_height') else '10'))
            if 'ninja_loss' in cached and hasattr(self, 'ninja_loss'):
                self.ninja_loss.delete(0, 'end')
                self.ninja_loss.insert(0, str(cached.get('ninja_loss') if cached.get('ninja_loss') else '14'))
            if 'ninja_tracking' in cached and hasattr(self, 'ninja_tracking'):
                val = cached.get('ninja_tracking') or DEFAULT_TRACKING
                self.ninja_tracking.set(val)
            if 'ninja_opt_angles' in cached and hasattr(self, 'ninja_opt_angles_var'):
                self.ninja_opt_angles_var.set(cached['ninja_opt_angles'])
            if 'ninja_tilt' in cached and hasattr(self, 'ninja_tilt'):
                self.ninja_tilt.delete(0, 'end')
                self.ninja_tilt.insert(0, str(cached.get('ninja_tilt', '')))
            if 'ninja_azimuth' in cached and hasattr(self, 'ninja_azimuth'):
                self.ninja_azimuth.delete(0, 'end')
                self.ninja_azimuth.insert(0, str(cached.get('ninja_azimuth', '')))
            if 'ninja_raw' in cached and hasattr(self, 'ninja_raw_var'):
                self.ninja_raw_var.set(cached['ninja_raw'])
        except Exception:
            pass
    
