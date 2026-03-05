# ui/source/components.py
# Shared UI components and helpers for Source Page

import customtkinter
import tkinter.ttk as ttk
import pandas as pd
import numpy as np
from .constants import *
from .units import get_column_unit, format_column_header


def create_metric_card(parent, title, value_str, description, row, column):
    """Create a KPI metric card - Modern design"""
    card = customtkinter.CTkFrame(
        parent, fg_color=BG_CARD, corner_radius=16,
        border_width=1, border_color=THEME.border.subtle,
        width=260, height=120
    )
    card.grid(row=row, column=column, padx=12, pady=12, sticky="nsew")
    card.grid_propagate(False)
    
    title_lbl = customtkinter.CTkLabel(
        card, text=title, font=(FONT_FAMILY_TEXT, 13), text_color=TEXT_SECONDARY
    )
    title_lbl.place(x=20, y=16)
    
    value_lbl = customtkinter.CTkLabel(
        card, text=value_str, font=(FONT_FAMILY_DISPLAY, 26, "bold"), text_color=TEXT_PRIMARY
    )
    value_lbl.place(x=20, y=44)
    
    desc_lbl = customtkinter.CTkLabel(
        card, text=description, font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_MUTED
    )
    desc_lbl.place(x=20, y=84)


def create_kpi_card(parent, title, value, unit, row, column):
    """Create a KPI metric card - Enhanced modern design"""
    card = customtkinter.CTkFrame(
        parent, fg_color=BG_CARD, corner_radius=16,
        border_width=1, border_color=THEME.border.subtle,
        width=220, height=140
    )
    card.grid(row=row, column=column, padx=12, pady=12, sticky="nsew")
    card.grid_propagate(False)
    
    # Title
    title_lbl = customtkinter.CTkLabel(
        card, text=title, font=(FONT_FAMILY_TEXT, 13), text_color=TEXT_SECONDARY
    )
    title_lbl.place(x=20, y=16)
    
    # Value
    value_lbl = customtkinter.CTkLabel(
        card, text=value, font=(FONT_FAMILY_DISPLAY, 28, "bold"), text_color=TEXT_PRIMARY
    )
    value_lbl.place(x=20, y=44)
    
    # Unit
    unit_lbl = customtkinter.CTkLabel(
        card, text=unit, font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_MUTED
    )
    unit_lbl.place(x=20, y=88)


def render_dataframe_table(parent, df, title="Data", context="import"):
    """
    High-end modern table rendering for DataFrames.
    Features: Card container, customTkinter styling, smooth scrollbars,
    alternating rows, modern header with app colors.
    """
    if df is None or df.empty:
        customtkinter.CTkLabel(
            parent,
            text="No data to display.",
            font=(FONT_FAMILY_TEXT, 12),
            text_color=TEXT_MUTED
        ).pack(pady=20)
        return
    
    # Modern card container - Enhanced design
    card_frame = customtkinter.CTkFrame(
        parent,
        fg_color=BG_CARD,
        corner_radius=16,
        border_width=1,
        border_color=BORDER_LIGHT
    )
    card_frame.pack(fill="both", expand=True, padx=24, pady=18)
    
    # Title header with modern blue accent
    header_frame = customtkinter.CTkFrame(
        card_frame,
        fg_color=PRIMARY_BLUE,
        corner_radius=20,
        height=56
    )
    header_frame.pack(fill="x", padx=2, pady=(2, 0))
    header_frame.pack_propagate(False)
    
    customtkinter.CTkLabel(
        header_frame,
        text=f"📊 {title}",
        font=(FONT_FAMILY_DISPLAY, 16, "bold"),
        text_color="#FFFFFF"
    ).pack(side="left", padx=24, pady=14)
    
    # Row count badge - Modern design
    count_badge = customtkinter.CTkFrame(
        header_frame,
        fg_color=PRIMARY_LIGHT,
        corner_radius=14,
        width=90,
        height=32
    )
    count_badge.pack(side="right", padx=24, pady=12)
    count_badge.pack_propagate(False)
    
    customtkinter.CTkLabel(
        count_badge,
        text=f"{fmt_num(len(df))} rows",
        font=(FONT_FAMILY_TEXT, 12, "bold"),
        text_color="#FFFFFF"
    ).place(relx=0.5, rely=0.5, anchor="center")
    
    # Table container
    table_container = customtkinter.CTkFrame(card_frame, fg_color="transparent")
    table_container.pack(fill="both", expand=True, padx=12, pady=12)
    table_container.grid_rowconfigure(0, weight=1)
    table_container.grid_columnconfigure(0, weight=1)
    
    # Configure modern styling
    style = ttk.Style()
    style.theme_use('clam')
    
    # Modern color scheme matching app
    bg_color = BG_CARD
    row_even = THEME.bg.table_even
    row_odd = BG_CARD
    header_bg = THEME.bg.gray_light
    select_bg = PRIMARY_BLUE
    text_primary_table = "#111827"
    text_secondary_table = THEME.text.gray_medium
    grid_color = THEME.border.gray
    
    # Main treeview style - Enhanced
    style.configure(
        "Modern.Treeview",
        background=bg_color,
        foreground=text_primary_table,
        fieldbackground=bg_color,
        rowheight=40,
        font=(FONT_FAMILY_TEXT, 13),
        borderwidth=0,
        relief="flat"
    )
    
    # Header style - Modern design
    style.configure(
        "Modern.Treeview.Heading",
        background=header_bg,
        foreground=text_primary_table,
        font=(FONT_FAMILY_TEXT, 13, "bold"),
        relief="flat",
        padding=(16, 12)
    )
    
    # Selection and alternating colors
    style.map(
        "Modern.Treeview",
        background=[
            ("selected", THEME.bg.selected_alt),
            ("!selected", row_odd)
        ],
        foreground=[("selected", PRIMARY_BLUE)]
    )
    
    # Remove default tree lines
    style.layout("Modern.Treeview", [
        ('Modern.Treeview.treearea', {'sticky': 'nswe'})
    ])
    
    # Treeview with dynamic columns
    columns = list(df.columns)
    tree = ttk.Treeview(
        table_container,
        columns=columns,
        show='headings',
        style="Modern.Treeview",
        selectmode='browse'
    )
    
    # Modern custom scrollbars
    vsb = customtkinter.CTkScrollbar(
        table_container,
        orientation="vertical",
        command=tree.yview,
        fg_color=THEME.bg.gray_light,
        button_color=THEME.border.medium,
        button_hover_color=THEME.text.gray_light,
        corner_radius=8
    )
    hsb = customtkinter.CTkScrollbar(
        table_container,
        orientation="horizontal",
        command=tree.xview,
        fg_color=THEME.bg.gray_light,
        button_color=THEME.border.medium,
        button_hover_color=THEME.text.gray_light,
        corner_radius=8
    )
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    
    tree.grid(row=0, column=0, sticky='nsew')
    vsb.grid(row=0, column=1, sticky='ns')
    hsb.grid(row=1, column=0, sticky='ew')
    
    # Column configuration with smart sizing
    for col in columns:
        dtype = df[col].dtype
        is_datetime = pd.api.types.is_datetime64_any_dtype(df[col])
        is_numeric = pd.api.types.is_numeric_dtype(df[col])
        is_time_col = any(keyword in str(col).lower() for keyword in ['time', 'date', 'utc'])
        
        if is_datetime or is_time_col:
            anchor = 'center'
            width = 170
        elif is_numeric:
            anchor = 'center'
            width = 120
        else:
            anchor = 'w'
            width = 140
        
        # Column header with unit
        unit = get_column_unit(col, context)
        display_name = format_column_header(str(col), unit)
        if len(display_name) > 20:
            display_name = display_name[:17] + "..."
            
        tree.heading(col, text=display_name, anchor='center')
        tree.column(col, width=width, anchor=anchor, minwidth=60, stretch=True)
    
    # Data insertion with alternating row tags
    for idx, (_, row) in enumerate(df.iterrows()):
        formatted_values = []
        for col, val in zip(columns, row):
            if pd.isna(val):
                formatted_values.append("")
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                formatted_values.append(pd.Timestamp(val).strftime("%Y-%m-%d %H:%M"))
            elif isinstance(val, (int, np.integer)):
                formatted_values.append(fmt_num(int(val)))
            elif isinstance(val, (float, np.floating)):
                if abs(val) >= 10000:
                    formatted_values.append(fmt_num(val, 0))
                else:
                    # Use 3 decimal places to match source import (e.g. Renewables.ninja, PVGIS)
                    formatted_values.append(f"{val:.3f}")
            else:
                formatted_values.append(str(val))
        
        # Alternate row colors
        tag = 'even' if idx % 2 == 0 else 'odd'
        tree.insert('', 'end', values=tuple(formatted_values), tags=(tag,))
    
    # Configure alternating row colors
    tree.tag_configure('even', background=row_even)
    tree.tag_configure('odd', background=row_odd)
    
    # Modern footer with stats
    footer_frame = customtkinter.CTkFrame(card_frame, fg_color="transparent", height=36)
    footer_frame.pack(fill="x", padx=16, pady=(0, 12))
    footer_frame.pack_propagate(False)
    
    # Stats on the left
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        first_col = numeric_cols[0]
        total = df[first_col].sum()
        avg = df[first_col].mean()
        
        stats_text = f"Sum: {fmt_num(total, 0)}  •  Avg: {avg:.1f}  •  {fmt_num(len(columns))} columns"
        customtkinter.CTkLabel(
            footer_frame,
            text=stats_text,
            font=(FONT_FAMILY_TEXT, 10),
            text_color=TEXT_SECONDARY
        ).pack(side="left", pady=8)
    
    return tree


def create_visualize_card(parent, title, subtitle, icon, column, command):
    """Apple-style data card – accent bar, tinted icon, 'View →' link."""
    card = customtkinter.CTkFrame(
        parent, corner_radius=14, border_width=1,
        border_color=THEME.border.subtle, fg_color=BG_CARD,
        cursor="hand2",
    )
    card.grid(row=0, column=column, padx=10, pady=8, sticky="nsew")

    # Thin accent bar at top
    customtkinter.CTkFrame(
        card, fg_color=THEME.primary.blue, height=3, corner_radius=0,
    ).pack(fill="x")

    # Icon in tinted circle
    ic_bg = customtkinter.CTkFrame(
        card, fg_color=THEME.primary.blue_light, corner_radius=20,
        width=44, height=44,
    )
    ic_bg.pack(pady=(22, 10))
    ic_bg.pack_propagate(False)
    customtkinter.CTkLabel(
        ic_bg, text=icon, font=(FONT_FAMILY_DISPLAY, 20),
    ).place(relx=.5, rely=.5, anchor="center")

    # Title
    customtkinter.CTkLabel(
        card, text=title, font=(FONT_FAMILY_TEXT, 15, "bold"),
        text_color=TEXT_PRIMARY,
    ).pack()

    # Subtitle
    customtkinter.CTkLabel(
        card, text=subtitle, font=(FONT_FAMILY_TEXT, 12),
        text_color=THEME.text.muted,
    ).pack(pady=(4, 14))

    # "View →" link
    link = customtkinter.CTkLabel(
        card, text="View →", font=(FONT_FAMILY_TEXT, 12, "bold"),
        text_color=THEME.primary.blue,
    )
    link.pack(pady=(0, 20))

    # Hover – bg shift, not border change
    def on_enter(e):
        card.configure(fg_color=THEME.bg.gray_pale, border_color=THEME.primary.blue)
        link.configure(text_color=THEME.primary.blue_hover)
    def on_leave(e):
        card.configure(fg_color=BG_CARD, border_color=THEME.border.subtle)
        link.configure(text_color=THEME.primary.blue)

    for w in [card] + list(card.winfo_children()):
        w.bind("<Button-1>", lambda e: command())
        w.bind("<Enter>", on_enter)
        w.bind("<Leave>", on_leave)


def create_data_card(parent, title, subtitle, on_click):
    """Create a clickable card for data sections"""
    card = customtkinter.CTkFrame(
        parent,
        fg_color=BG_CARD,
        corner_radius=CORNER_RADIUS_CARD,
        border_width=1,
        border_color=BORDER_LIGHT
    )
    card.pack(fill="x", pady=(0, 12), padx=10)

    inner = customtkinter.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="x", padx=20, pady=16)

    # Text side
    text_frame = customtkinter.CTkFrame(inner, fg_color="transparent")
    text_frame.pack(side="left", fill="x", expand=True)

    title_label = customtkinter.CTkLabel(
        text_frame,
        text=title,
        font=(FONT_FAMILY_TEXT, 14, "bold"),
        text_color=TEXT_PRIMARY
    )
    title_label.pack(anchor="w")

    subtitle_label = customtkinter.CTkLabel(
        text_frame,
        text=subtitle,
        font=(FONT_FAMILY_TEXT, 11),
        text_color=TEXT_SECONDARY
    )
    subtitle_label.pack(anchor="w")

    # Arrow icon on the right
    arrow_label = customtkinter.CTkLabel(
        inner,
        text="›",
        font=(FONT_FAMILY_TEXT, 24),
        text_color=TEXT_MUTED
    )
    arrow_label.pack(side="right")

    # Make the whole card clickable
    def handle_click(_event=None):
        on_click()

    for widget in (card, inner, text_frame, title_label, subtitle_label, arrow_label):
        widget.bind("<Button-1>", handle_click)
        widget.configure(cursor="hand2")

    return card


def add_summary_row(parent, label_text, value_text):
    """Add a label-value row for summary displays"""
    row = customtkinter.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=20, pady=4)
    
    label = customtkinter.CTkLabel(
        row, text=label_text, font=(FONT_FAMILY_TEXT, 12, "bold"), text_color=THEME.text.gray_dark
    )
    label.pack(side="left")
    
    value = customtkinter.CTkLabel(
        row, text=value_text, font=(FONT_FAMILY_TEXT, 12), text_color=TEXT_SECONDARY
    )
    value.pack(side="left", padx=(8, 0))
