# ui/source/step3_export.py
# Step 3: Save & Export functionality

import customtkinter
from .constants import *
from .components import add_summary_row


class Step3ExportMixin:
    """
    Step 3: Save & Export functionality
    """
    
    def _build_step3_export(self):
        """Build Step 3 UI inside content_inner only"""
        subtitle = customtkinter.CTkLabel(
            self.content_inner, text="Summary and export",
            font=(FONT_FAMILY_TEXT, 13), text_color=TEXT_SECONDARY
        )
        subtitle.pack(anchor="w", pady=(0, 16))
        
        summary_frame = customtkinter.CTkFrame(
            self.content_inner, fg_color=BG_CARD,
            corner_radius=CORNER_RADIUS_CARD, border_width=1, border_color=BORDER_LIGHT
        )
        summary_frame.pack(fill="x", pady=(0, 16))
        
        config = self.import_config or {}
        source = config.get("source", "Unknown")
        
        add_summary_row(summary_frame, "Data source:", source)
        
        lat = config.get("latitude", "N/A")
        lon = config.get("longitude", "N/A")
        add_summary_row(summary_frame, "Location:", f"Lat {lat}, Lon {lon}")
        
        if source == "PVGIS":
            mode = config.get("pvgis_mode", "Unknown")
            if mode == "HOURLY":
                start = config.get("start_year", "N/A")
                end = config.get("end_year", "N/A")
                add_summary_row(summary_frame, "Mode:", f"Hourly data ({start}-{end})")
            else:
                period = config.get("tmy_database", "N/A")
                add_summary_row(summary_frame, "Mode:", f"TMY period: {period}")
            
            peak = config.get("peak_power_kwp", "N/A")
            loss = config.get("system_loss_percent", "N/A")
            add_summary_row(summary_frame, "PV system:", f"Peak power: {peak} kWp, System loss: {loss}%")
        else:
            year = config.get("year", "N/A")
            add_summary_row(summary_frame, "Year:", str(year))
            cap = config.get("capacity_kw", "N/A")
            loss = config.get("system_loss_fraction", "N/A")
            if isinstance(loss, (int, float)):
                loss = f"{loss*100:.0f}%"
            add_summary_row(summary_frame, "PV system:", f"Capacity: {cap} kW, System loss: {loss}")
        
        store_checkbox = customtkinter.CTkCheckBox(
            self.content_inner,
            text="Store this dataset in project for later use (Desalination & Economics)",
            variable=self.store_in_project_var,
            font=(FONT_FAMILY_TEXT, 13), text_color="#374151"
        )
        store_checkbox.pack(anchor="w", pady=(0, 16))
        
        export_frame = customtkinter.CTkFrame(self.content_inner, fg_color="transparent")
        export_frame.pack(anchor="w", pady=(0, 10))
        
        excel_button = customtkinter.CTkButton(
            export_frame, text="Export to Excel (.xlsx)", command=self._export_to_excel,
            fg_color=PRIMARY_BLUE, hover_color=PRIMARY_HOVER, text_color="#FFFFFF",
            corner_radius=CORNER_RADIUS_BUTTON
        )
        excel_button.pack(side="left", padx=(0, 10))
        
        csv_button = customtkinter.CTkButton(
            export_frame, text="Export to CSV", command=self._export_to_csv,
            fg_color=BG_CARD, hover_color="#F3F4F6", text_color="#374151",
            border_width=1, border_color="#D1D5DB", corner_radius=CORNER_RADIUS_BUTTON
        )
        csv_button.pack(side="left")
        
        self.export_status_label = customtkinter.CTkLabel(
            self.content_inner, text="", font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
        )
        self.export_status_label.pack(anchor="w", pady=(8, 0))

    def _export_to_excel(self):
        self.export_status_label.configure(
            text="✓ Data exported to Excel successfully (dummy implementation)",
            text_color=SUCCESS_GREEN
        )
        print("Export to Excel called - not yet implemented")

    def _export_to_csv(self):
        self.export_status_label.configure(
            text="✓ Data exported to CSV successfully (dummy implementation)",
            text_color=SUCCESS_GREEN
        )
        print("Export to CSV called - not yet implemented")

    def _finish_source_workflow(self):
        if hasattr(self, "store_in_project_var") and self.store_in_project_var.get():
            self.app.source_data = {
                "import_config": self.import_config,
                "hourly_data": self._view_hourly if hasattr(self, "_view_hourly") else None
            }
            print("Source data stored in app.source_data for later modules")
        
        self.app.store.complete_section("source")
        self.app.show_home_page()
