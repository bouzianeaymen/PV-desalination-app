"""
Fetch hourly data with fixed mounting (same params as Step 1) for Energy step tracking coefficient.
Used when Step 1 mounting was not fixed: we need Psource(f) to compute Kt = Psource(x)/Psource(f).
"""
import pandas as pd
from typing import Dict, Any, Optional, Tuple


def _derive_mounting(import_config: Dict[str, Any], source: str) -> str:
    """Derive mounting from config. Ninja: map tracking to mounting (like PVGIS)."""
    if (source or "").upper() == "NINJA" and (import_config.get("ninja_mode") or "PV").upper() == "PV":
        tracking = (import_config.get("tracking") or "None").strip()
        return {"None": "fixed", "Single-axis": "inclined_axis", "Dual-axis": "two_axis"}.get(
            tracking, "fixed"
        )
    return (import_config.get("mounting_type") or import_config.get("mounting") or "fixed").lower()


def fetch_fixed_mounting_hourly(import_config: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Fetch hourly data with fixed mounting using same location/period as import_config.
    Returns (hourly_data DataFrame, error_message). Empty string on success.
    """
    if not import_config:
        return (None, "No import config.")
    source = (import_config.get("source") or "").upper()
    mounting = _derive_mounting(import_config, source)
    if mounting == "fixed":
        return (None, "")  # Caller will use same df for both

    if source == "PVGIS":
        return _fetch_pvgis_fixed(import_config)
    if "NINJA" in source:
        ninja_mode = (import_config.get("ninja_mode") or "PV").upper()
        if ninja_mode == "PV":
            return _fetch_ninja_pv_fixed(import_config)
        return (None, "Wind data: fixed equivalent not implemented.")
    return (None, "Unknown source for fixed import.")


def _fetch_pvgis_fixed(cfg: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], str]:
    try:
        from source.pvgis_client import fetch_pvgis_hourly
    except ImportError:
        return (None, "PVGIS client not available.")
    lat = cfg.get("latitude")
    lon = cfg.get("longitude")
    database = cfg.get("database", "PVGIS-ERA5")
    start_year = cfg.get("start_year")
    end_year = cfg.get("end_year")
    power = cfg.get("peak_power_kwp", 1.0)
    loss = cfg.get("system_loss_percent", 14)
    tech = cfg.get("pv_technology", "Crystalline Silicon")
    alt = cfg.get("altitude")
    include_comp = cfg.get("radiation_components", False)
    if lat is None or lon is None or start_year is None or end_year is None:
        return (None, "Missing PVGIS params (lat, lon, years).")
    try:
        result = fetch_pvgis_hourly(
            latitude=float(lat),
            longitude=float(lon),
            start_year=int(start_year),
            end_year=int(end_year),
            peak_power_kwp=float(power),
            system_loss_percent=float(loss),
            mounting_type="fixed",
            slope=None,
            azimuth=None,
            database=database,
            optimize_slope=False,
            optimize_slope_azimuth=True,
            altitude=float(alt) if alt is not None else None,
            pv_technology=tech,
            include_components=include_comp,
        )
    except Exception as e:
        return (None, f"Fixed-mounting fetch failed: {str(e)}")
    hourly = result.get("hourly_data") if isinstance(result, dict) else None
    if hourly is None or (hasattr(hourly, "empty") and hourly.empty):
        return (None, "No hourly data returned for fixed mounting.")
    return (hourly, "")


def _fetch_ninja_pv_fixed(cfg: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], str]:
    try:
        from source.ninja_client import fetch_ninja_pv
    except ImportError:
        return (None, "Ninja client not available.")
    lat = cfg.get("latitude")
    lon = cfg.get("longitude")
    year = cfg.get("year")
    dataset = cfg.get("dataset", "MERRA-2 (global)")
    capacity = cfg.get("capacity_kw") or cfg.get("capacity") or 1.0
    loss_frac = cfg.get("system_loss_fraction", 0.14)
    tilt = cfg.get("tilt")
    azimuth = cfg.get("azimuth")
    include_raw = cfg.get("include_raw", False)
    if lat is None or lon is None or year is None:
        return (None, "Missing Ninja params (lat, lon, year).")
    tilt = float(tilt) if tilt is not None else 30.0
    azimuth = float(azimuth) if azimuth is not None else 0.0
    try:
        result = fetch_ninja_pv(
            latitude=float(lat),
            longitude=float(lon),
            year=int(year),
            dataset=dataset,
            capacity_kw=float(capacity),
            system_loss_fraction=float(loss_frac),
            tracking_mode="None",
            tilt_deg=tilt,
            azimuth_deg=azimuth,
            include_raw=include_raw,
        )
    except Exception as e:
        return (None, f"Fixed-mounting fetch failed: {str(e)}")
    hourly = result.get("hourly_data") if isinstance(result, dict) else None
    if hourly is None or (hasattr(hourly, "empty") and hourly.empty):
        return (None, "No hourly data returned for fixed mounting.")
    return (hourly, "")
