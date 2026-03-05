# ui/source/units.py
# Column name → unit mapping for visualization, export, and metadata

# Energy step result columns (from run_energy_calculation)
ENERGY_COLUMN_UNITS = {
    "time": "",
    "Ta": "°C",
    "TC(f)": "°C",
    "Ppv(f)": "W",
    "Psource(f)": "W",
    "Psource(x)": "W",
    "Kt": "",
    "Ppv(x)": "W",
    "Epv(f)": "Wh",
    "Epv(x)": "Wh",
    "Esource(f)": "Wh",
    "Esource(x)": "Wh",
    "CF(f)": "%",
    "CF(x)": "%",
}

# Import data columns (PVGIS, Ninja) - known column names
# Hourly: P = power (W), G* = irradiance (W/m²). Monthly/Yearly: E = energy (Wh); G* keep name, unit Wh/m²
IMPORT_COLUMN_UNITS = {
    "G(i)": "W/m²",
    "G(h)": "W/m²",
    "Gb(i)": "W/m²",
    "Gd(i)": "W/m²",
    "Gr(i)": "W/m²",
    "T2m": "°C",
    "Tamb": "°C",
    "temp": "°C",
    "WS10m": "m/s",
    "wind_speed": "m/s",
    "windspeed": "m/s",
    "P": "W",
    "electricity": "kWh",
    "irradiance_direct": "W/m²",
    "irradiance_diffuse": "W/m²",
    "time(UTC)": "",
    "time": "",
    # Aggregated (monthly/yearly): power column renamed to energy
    "E": "Wh",
    "Esource": "Wh",
}

# Irradiance columns: same name in hourly and monthly/yearly; unit W/m² hourly; kWh/m² or MWh/m² when aggregated
IRRADIANCE_COLS = frozenset({"G(i)", "G(h)", "Gb(i)", "Gd(i)", "Gr(i)"})

# Energy columns (energy step): Epv, Esource; monthly → kWh, yearly → MWh
ENERGY_STEP_AGG_COLS = frozenset({"Epv(f)", "Epv(x)", "Esource(f)", "Esource(x)"})

# Energy columns (import aggregated): E, Esource, electricity
IMPORT_ENERGY_COLS = frozenset({"E", "Esource", "electricity"})


def get_column_unit(col_name: str, context: str = "energy", view: str = None) -> str:
    """Return unit for column. context: 'energy' | 'import'. view: 'hourly' | 'monthly' | 'yearly' for aggregated units (kWh/MWh)."""
    col = str(col_name).strip()
    # Energy step: hourly = Wh; daily/monthly = kWh, yearly = MWh
    if context == "energy":
        base = ENERGY_COLUMN_UNITS.get(col, "")
        if view in ("daily", "monthly") and col in ENERGY_STEP_AGG_COLS:
            return "kWh"
        if view == "yearly" and col in ENERGY_STEP_AGG_COLS:
            return "MWh"
        return base
    # Import: hourly = W, W/m²; monthly = kWh, kWh/m²; yearly = MWh, MWh/m²
    mapping = {**ENERGY_COLUMN_UNITS, **IMPORT_COLUMN_UNITS}
    unit = mapping.get(col, "")
    if view == "monthly":
        if col in IMPORT_ENERGY_COLS:
            return "kWh"
        if col in IRRADIANCE_COLS:
            return "kWh/m²"
    if view == "yearly":
        if col in IMPORT_ENERGY_COLS:
            return "MWh"
        if col in IRRADIANCE_COLS:
            return "MWh/m²"
    return unit


def format_column_header(col_name: str, unit: str) -> str:
    """Return display string for column header with optional unit."""
    if unit:
        return f"{col_name} ({unit})"
    return col_name
