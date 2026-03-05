"""
TC and Ppv model definitions and computation for Energy step.
Variables = from Step 1 data; Constants = from panel (SAM) or fixed.
"""
import warnings
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List

# TC models (Modèle N°1 = NOCT-style, N°2 = U_0/U_1 wind, N°3 = NOCT with wind)
TC_MODELS = {
    "NOCT-style": {
        "name": "NOCT-style",
        "equation": "Tc = Tamb + (NOCT - 20) × (G / 800)",
        "variables": ["Tamb", "G"],
        "constants": ["NOCT"],
        "description": "Cell temperature from ambient and irradiance.",
    },
    "Modèle N°2": {
        "name": "Modèle N°2",
        "equation": "Tc = Ta + G / (U_0 + U_1 × V_v)",
        "variables": ["Ta", "G", "V_v"],
        "constants": ["U_0", "U_1"],
        "description": "Cell temperature from ambient, irradiance and wind speed.",
    },
    "Modèle N°3": {
        "name": "Modèle N°3",
        "equation": "Tc = Ta + ((TNOCT - 20) / (800 + h×((Vv-V0)/V0)×(TNOCT-20))) × G, with h = 3.8×Vv + 5.7",
        "variables": ["Ta", "G", "Vv"],
        "constants": ["TNOCT", "V0"],
        "description": "NOCT-style cell temperature with wind correction. h (heat transfer) = 3.8×Vv + 5.7 from wind speed (PVGIS: WS10m, Ninja: wind_speed).",
    },
}

# Ppv models (IEC nomenclature: Standard, Radziemska, Mattei)
PPV_MODELS = {
    "Standard": {
        "name": "Standard",
        "equation": "Pout = Pnom × (G/G_stc) × [1 + γp × (Tc − Tref)]",
        "variables": ["G", "Tc"],
        "constants": ["Pnom", "G_stc", "γp", "Tref"],
        "description": "Standard site power (IEC). Uses cell temperature from TC model.",
    },
    "Radziemska": {
        "name": "Radziemska",
        "equation": "Pout = Pnom × (G/G_stc) × [1 + γp × (Ta + kradz×G − Tref)]",
        "variables": ["G", "Ta"],
        "constants": ["Pnom", "G_stc", "γp", "Tref", "kradz"],
        "description": "Empirical: ambient Ta + kradz×G estimates cell heating.",
    },
    "Mattei": {
        "name": "Mattei",
        "equation": "Pout = Pnom × (G/G_stc) × [1 + γp×(Tc−Tref) + δ×ln(G/G_stc)]",
        "variables": ["G", "Tc"],
        "constants": ["Pnom", "G_stc", "γp", "Tref", "δ"],
        "description": "Non-linear irradiance: log term corrects low-G efficiency.",
    },
}


def _detect_columns(df: pd.DataFrame, source: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Return (time_col, G_col, Tamb_col, W_col) from hourly DataFrame. source in ('PVGIS','NINJA').
    Prefer G(i)=total in-plane irradiance over Gb(i)/Gd(i) when radiation components are present."""
    time_col = None
    G_col = None
    G_candidates: List[str] = []
    Tamb_col = None
    W_col = None
    cols = list(df.columns)
    for c in cols:
        c_lower = str(c).lower()
        if "time" in c_lower and time_col is None:
            time_col = c
        if c in ("G(h)", "G(i)", "Gb(i)", "Gd(i)", "G", "irradiance") or "ghi" in c_lower or (c_lower.startswith("g") and "(" in c):
            G_candidates.append(c)
        if c in ("T2m", "Tamb", "temp", "temperature", "t_air") or "temp" in c_lower or "t2m" in c_lower:
            if Tamb_col is None:
                Tamb_col = c
        if c in ("WS10m", "wind_speed", "windspeed", "ws", "v wind", "wind") or "wind" in c_lower or "ws10" in c_lower:
            if W_col is None:
                W_col = c
    # Prefer G(i) (total in-plane) over Gb(i)/Gd(i) (beam/diffuse only)
    G_PREFERENCE = ("G(i)", "G(h)", "G", "irradiance", "Gb(i)", "Gd(i)")
    for preferred in G_PREFERENCE:
        for c in G_candidates:
            if c == preferred:
                G_col = c
                break
        if G_col is not None:
            break
    if G_col is None and G_candidates:
        G_col = G_candidates[0]
    if not time_col and len(cols):
        time_col = cols[0]
    return (time_col, G_col, Tamb_col, W_col)


def compute_tc_noct(
    df: pd.DataFrame,
    noct: float,
    time_col: Optional[str],
    G_col: Optional[str],
    Tamb_col: Optional[str],
) -> pd.Series:
    """Tc = Tamb + (NOCT - 20) * (G / 800). Missing G or Tamb -> NaN for that row."""
    out = pd.Series(index=df.index, dtype=float)
    out[:] = np.nan
    if Tamb_col is None or G_col is None:
        return out
    G = pd.to_numeric(df[G_col], errors="coerce")
    Tamb = pd.to_numeric(df[Tamb_col], errors="coerce")
    out = Tamb + (noct - 20) * (G / 800.0)
    return out


def compute_tc_model2(
    df: pd.DataFrame,
    u0: float,
    u1: float,
    time_col: Optional[str],
    G_col: Optional[str],
    Tamb_col: Optional[str],
    W_col: Optional[str],
    clip_tc: bool = True,
) -> pd.Series:
    """Tc = Ta + G / (U_0 + U_1 * V_v). If W_col is None, use Vv=1. Optional clip to [Tamb-10, Tamb+80]."""
    out = pd.Series(index=df.index, dtype=float)
    out[:] = np.nan
    if Tamb_col is None or G_col is None:
        return out
    G = pd.to_numeric(df[G_col], errors="coerce")
    Ta = pd.to_numeric(df[Tamb_col], errors="coerce")
    if W_col is not None and W_col in df.columns:
        Vv = pd.to_numeric(df[W_col], errors="coerce").fillna(1.0).clip(lower=0.1)
    else:
        Vv = 1.0
    denom = u0 + u1 * Vv
    with np.errstate(divide="ignore", invalid="ignore"):
        tc = Ta + np.where(denom > 0, G / denom, np.nan)
    if clip_tc:
        tc = np.clip(tc, Ta - 10.0, Ta + 80.0)
    out = pd.Series(tc, index=df.index)
    return out


def compute_tc_model3(
    df: pd.DataFrame,
    tnoct: float,
    v0: float,
    time_col: Optional[str],
    G_col: Optional[str],
    Tamb_col: Optional[str],
    W_col: Optional[str],
    clip_tc: bool = True,
) -> pd.Series:
    """Tc = Ta + ((TNOCT - 20) / (800 + h×((Vv-V0)/V0)×(TNOCT-20))) × G.
    h = 3.8 * Vv + 5.7 (convective heat transfer, varies with wind speed).
    W_col maps to wind speed from PVGIS (WS10m) or Ninja (wind_speed). If no wind column, use Vv=V0."""
    out = pd.Series(index=df.index, dtype=float)
    out[:] = np.nan
    if Tamb_col is None or G_col is None:
        return out
    v0_safe = max(float(v0), 1e-6)
    G = pd.to_numeric(df[G_col], errors="coerce")
    Ta = pd.to_numeric(df[Tamb_col], errors="coerce")
    if W_col is not None and W_col in df.columns:
        Vv = pd.to_numeric(df[W_col], errors="coerce").fillna(v0_safe).clip(lower=0.0)
    else:
        Vv = v0_safe
    # h = 3.8 * Vv + 5.7 (W/m²·K, convective heat transfer coefficient)
    h = 3.8 * Vv + 5.7
    num = (tnoct - 20.0)
    denom_extra = h * ((Vv - v0_safe) / v0_safe) * (tnoct - 20.0)
    denom = 800.0 + denom_extra
    denom = np.where(denom > 0, denom, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        tc = Ta + (num / denom) * G
    if clip_tc:
        tc = np.clip(tc, Ta - 10.0, Ta + 80.0)
    out = pd.Series(tc, index=df.index)
    return out


def compute_ppv_standard(
    df: pd.DataFrame,
    tc_series: pd.Series,
    gamma: float,
    G_stc: float,
    T_stc: float,
    P_stc: float,
    G_col: Optional[str],
) -> pd.Series:
    """Pout = Pnom × (G/G_stc) × [1 + γp × (Tc − Tref)]. IEC Standard model. G=0 or NaN → 0."""
    out = pd.Series(index=df.index, dtype=float)
    out[:] = 0.0
    if G_col is None:
        return out
    G = pd.to_numeric(df[G_col], errors="coerce").fillna(0)
    tc = tc_series.fillna(T_stc)
    factor = (G / G_stc).replace(0, np.nan)
    out = P_stc * factor * (1 + gamma * (tc - T_stc))
    return out.fillna(0).clip(lower=0)


def compute_ppv_radziemska(
    df: pd.DataFrame,
    gamma: float,
    G_stc: float,
    T_stc: float,
    P_stc: float,
    kradz: float,
    G_col: Optional[str],
    Tamb_col: Optional[str],
) -> pd.Series:
    """Pout = Pnom × (G/G_stc) × [1 + γp × (Ta + kradz×G − Tref)]. Uses ambient Ta, not Tc. G=0 or NaN → 0."""
    out = pd.Series(index=df.index, dtype=float)
    out[:] = 0.0
    if G_col is None or Tamb_col is None:
        return out
    G = pd.to_numeric(df[G_col], errors="coerce").fillna(0)
    Ta = pd.to_numeric(df[Tamb_col], errors="coerce").fillna(T_stc)
    factor = (G / G_stc).replace(0, np.nan)
    temp_term = Ta + kradz * G - T_stc
    out = P_stc * factor * (1 + gamma * temp_term)
    return out.fillna(0).clip(lower=0)


def compute_ppv_mattei(
    df: pd.DataFrame,
    tc_series: pd.Series,
    gamma: float,
    delta: float,
    G_stc: float,
    T_stc: float,
    P_stc: float,
    G_col: Optional[str],
) -> pd.Series:
    """Pout = Pnom × (G/G_stc) × [1 + γp×(Tc−Tref) + δ×ln(G/G_stc)]. ln argument clipped to avoid <=0. G=0 or NaN → 0."""
    out = pd.Series(index=df.index, dtype=float)
    out[:] = 0.0
    if G_col is None:
        return out
    G = pd.to_numeric(df[G_col], errors="coerce").fillna(0)
    ratio = (G / G_stc).clip(lower=1e-10)
    log_term = np.log(ratio)
    bracket = 1.0 + gamma * (tc_series.fillna(T_stc) - T_stc) + delta * log_term
    out = P_stc * bracket * (G / G_stc)
    return out.fillna(0).clip(lower=0)


def aggregate_energy_hourly(
    hourly_df: pd.DataFrame,
    rule: str,
    add_month_year: bool = False,
) -> pd.DataFrame:
    """Aggregate hourly energy: power cols SUM (→Epv, Esource in Wh); TC, Kt MEAN.
    rule: 'D'|'ME'|'YE'. Returns DataFrame with time index reset."""
    df = hourly_df.copy()
    time_col = None
    for c in df.columns:
        if "time" in str(c).lower():
            time_col = c
            break
    if time_col is None:
        return pd.DataFrame()
    col = df[time_col]
    if pd.api.types.is_datetime64_any_dtype(col):
        df[time_col] = pd.to_datetime(col, utc=True, errors="coerce")
    else:
        sample = col.dropna()
        if len(sample) > 0:
            first = str(sample.iloc[0])
            if ":" in first and len(first) <= 16:
                df[time_col] = pd.to_datetime(col, format="%Y%m%d:%H%M", utc=True, errors="coerce")
            elif pd.api.types.is_numeric_dtype(col):
                df[time_col] = pd.to_datetime(col, unit="ms", utc=True, errors="coerce")
            else:
                df[time_col] = pd.to_datetime(col, utc=True, errors="coerce")
        else:
            df[time_col] = pd.to_datetime(col, utc=True, errors="coerce")
    df = df.dropna(subset=[time_col])
    if df.empty:
        return pd.DataFrame()
    df = df.sort_values(time_col)
    df = df.set_index(time_col)
    POWER_COLS = {"Ppv(f)", "Ppv(x)", "Psource(f)", "Psource(x)"}
    sum_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c in POWER_COLS]
    mean_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in POWER_COLS]
    parts = []
    if sum_cols:
        parts.append(df.resample(rule)[sum_cols].sum())
    if mean_cols:
        parts.append(df.resample(rule)[mean_cols].mean())
    agg = pd.concat(parts, axis=1) if len(parts) > 1 else (parts[0] if parts else pd.DataFrame())
    if agg.empty:
        return pd.DataFrame()
    rename_map = {
        "Ppv(f)": "Epv(f)",
        "Ppv(x)": "Epv(x)",
        "Psource(f)": "Esource(f)",
        "Psource(x)": "Esource(x)",
    }
    agg = agg.rename(columns={k: v for k, v in rename_map.items() if k in agg.columns})
    # Energy-weighted Kt (ratio Esource(x)/Esource(f)) instead of mean(hourly Kt) for physical sense
    if "Esource(f)" in agg.columns and "Esource(x)" in agg.columns and "Kt" in agg.columns:
        ef = pd.to_numeric(agg["Esource(f)"], errors="coerce").fillna(0).values
        ex = pd.to_numeric(agg["Esource(x)"], errors="coerce").fillna(0).values
        with np.errstate(divide="ignore", invalid="ignore"):
            kt_agg = np.where(ef > 0, ex / ef, 1.0)
        agg["Kt"] = np.clip(kt_agg, 0.0, 2.5)
    # Daily/monthly → kWh, yearly → MWh (data stored in scaled units for display)
    energy_cols = [c for c in ("Epv(f)", "Epv(x)", "Esource(f)", "Esource(x)") if c in agg.columns]
    if rule in ("D", "ME") and energy_cols:
        agg[energy_cols] = agg[energy_cols] / 1000.0
    elif rule == "YE" and energy_cols:
        agg[energy_cols] = agg[energy_cols] / 1e6
    agg = agg.reset_index()
    if add_month_year and rule == "ME":
        agg["Month"] = agg[time_col].dt.month
        agg["Year"] = agg[time_col].dt.year
    # Ensure energy columns have no NaN (physical sense)
    for c in ("Epv(f)", "Epv(x)", "Esource(f)", "Esource(x)"):
        if c in agg.columns:
            agg[c] = pd.to_numeric(agg[c], errors="coerce").fillna(0).clip(lower=0)
    return agg


def add_cf_columns(
    agg_df: pd.DataFrame,
    rule: str,
    peak_kw: float,
) -> pd.DataFrame:
    """
    Add CF(f), CF(x) (capacity factor in %) to aggregated energy df.
    CF = Epv / (P_nom * hours) * 100. rule: 'D'|'ME'|'YE'.
    """
    if agg_df is None or agg_df.empty or peak_kw <= 0:
        return agg_df
    time_col = next((c for c in agg_df.columns if "time" in str(c).lower()), None)
    if not time_col:
        return agg_df
    t = pd.to_datetime(agg_df[time_col], utc=True, errors="coerce")
    if rule == "D":
        hours = 24.0
    elif rule == "ME":
        hours = t.dt.days_in_month.values.astype(float) * 24.0
    elif rule == "YE":
        hours = 8760.0
    else:
        return agg_df
    denom = peak_kw * hours
    if np.isscalar(denom):
        denom = np.full(len(agg_df), denom)
    denom = np.where(denom <= 0, np.nan, denom)
    out = agg_df.copy()
    for ecol, cfcol in [("Epv(f)", "CF(f)"), ("Epv(x)", "CF(x)")]:
        if ecol in agg_df.columns:
            e = pd.to_numeric(agg_df[ecol], errors="coerce").fillna(0).values
            if rule == "YE":
                e = e * 1000.0
            cf = np.where(denom > 0, (e / denom) * 100.0, 0.0)
            out[cfcol] = cf
    return out


def _source_power_column(df: pd.DataFrame) -> Optional[str]:
    """Return column name for source power (P or electricity)."""
    for col in ("P", "electricity", "power"):
        if col in df.columns:
            return col
    for c in df.columns:
        if "power" in str(c).lower() or "electric" in str(c).lower():
            return c
    return None


def run_energy_calculation(
    hourly_df: pd.DataFrame,
    source: str,
    panel: Dict[str, Any],
    peak_power_kw: float,
    tc_model_id: str = "NOCT-style",
    ppv_model_id: str = "Standard",
    mounting_type: Optional[str] = None,
    hourly_fixed_df: Optional[pd.DataFrame] = None,
) -> Tuple[pd.DataFrame, str]:
    """
    Run TC(f) and Ppv(f); optionally add Psource(f), Psource(x), Kt, Ppv(x) when tracking.
    Returns (DataFrame), message (empty if ok; info if fallback).
    """
    if hourly_df is None or hourly_df.empty:
        return (pd.DataFrame(), "No hourly data from Step 1.")
    # Compute G(i) from components when no single G column exists
    df = hourly_df.copy()
    if "G(i)" not in df.columns and all(c in df.columns for c in ("Gb(i)", "Gd(i)", "Gr(i)")):
        df["G(i)"] = (
            pd.to_numeric(df["Gb(i)"], errors="coerce").fillna(0)
            + pd.to_numeric(df["Gd(i)"], errors="coerce").fillna(0)
            + pd.to_numeric(df["Gr(i)"], errors="coerce").fillna(0)
        )
    elif "G(i)" not in df.columns and all(c in df.columns for c in ("irradiance_direct", "irradiance_diffuse")):
        # Ninja raw: Gi = direct + diffuse
        df["G(i)"] = (
            pd.to_numeric(df["irradiance_direct"], errors="coerce").fillna(0)
            + pd.to_numeric(df["irradiance_diffuse"], errors="coerce").fillna(0)
        )
    time_col, G_col, Tamb_col, W_col = _detect_columns(df, source)
    u0 = float(panel.get("U_0", 25.0))
    u1 = float(panel.get("U_1", 6.84))
    if G_col is None or Tamb_col is None:
        pcol = _source_power_column(df)
        if not pcol:
            return (pd.DataFrame(), "No irradiance (G) or ambient temp (Tamb) in data, and no power column found.")
        out = pd.DataFrame(index=df.index)
        if time_col:
            out["time"] = df[time_col].values
        out["Psource(x)"] = pd.to_numeric(df[pcol], errors="coerce").fillna(0).clip(lower=0).values
        return (out, "Showing source power only. TC/Ppv require G and Tamb (e.g. from PVGIS hourly).")
    noct = float(panel.get("NOCT", 45))
    gamma = float(panel.get("gamma", -0.004))
    G_stc = float(panel.get("G_stc", 1000))
    T_stc = float(panel.get("T_stc", 25))
    P_stc = peak_power_kw * 1000.0  # W
    v0_tc3 = float(panel.get("V0", 1.0))
    delta_mattei = float(panel.get("delta", 0.12))
    kradz = float(panel.get("kradz", 0.02))
    if tc_model_id == "Modèle N°2":
        tc_series = compute_tc_model2(df, u0, u1, time_col, G_col, Tamb_col, W_col)
    elif tc_model_id == "Modèle N°3":
        tc_series = compute_tc_model3(df, noct, v0_tc3, time_col, G_col, Tamb_col, W_col)
    else:
        tc_series = compute_tc_noct(df, noct, time_col, G_col, Tamb_col)
    if ppv_model_id == "Radziemska":
        ppv_series = compute_ppv_radziemska(df, gamma, G_stc, T_stc, P_stc, kradz, G_col, Tamb_col)
    elif ppv_model_id == "Mattei":
        ppv_series = compute_ppv_mattei(df, tc_series, gamma, delta_mattei, G_stc, T_stc, P_stc, G_col)
    else:
        ppv_series = compute_ppv_standard(df, tc_series, gamma, G_stc, T_stc, P_stc, G_col)
    out = pd.DataFrame(index=df.index)
    if time_col:
        out["time"] = df[time_col].values
    out["TC(f)"] = tc_series.values
    out["Ppv(f)"] = ppv_series.values
    if Tamb_col is not None and Tamb_col in df.columns:
        out["Ta"] = pd.to_numeric(df[Tamb_col], errors="coerce").values

    pcol = _source_power_column(df)
    if not pcol:
        return (out, "")
    psource_x = pd.to_numeric(df[pcol], errors="coerce")
    mounting = (mounting_type or "fixed").lower()
    if mounting == "fixed" or hourly_fixed_df is None or hourly_fixed_df.empty:
        out["Psource(f)"] = psource_x.fillna(0).clip(lower=0).values
        out["Psource(x)"] = psource_x.fillna(0).clip(lower=0).values
        out["Kt"] = 1.0
        out["Ppv(x)"] = ppv_series.values  # already non-negative from compute_ppv_*
        _sanitize_energy_output(out)
        return (out, "")
    # Align fixed to current by time
    time_col_f, _, _, _ = _detect_columns(hourly_fixed_df, source)
    pcol_f = _source_power_column(hourly_fixed_df)
    if not time_col_f or not pcol_f:
        out["Psource(f)"] = psource_x.fillna(0).clip(lower=0).values
        out["Psource(x)"] = psource_x.fillna(0).clip(lower=0).values
        out["Kt"] = 1.0
        out["Ppv(x)"] = ppv_series.values
        _sanitize_energy_output(out)
        return (out, "Could not align fixed data; showing fixed = x.")
    psource_f_raw = pd.to_numeric(hourly_fixed_df[pcol_f], errors="coerce")
    n_x, n_f = len(df), len(hourly_fixed_df)
    if n_x == n_f:
        psource_f_aligned = psource_f_raw.values
    elif time_col and time_col_f:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            t_x = pd.to_datetime(df[time_col], utc=True, errors="coerce")
            t_fixed = pd.to_datetime(hourly_fixed_df[time_col_f], utc=True, errors="coerce")
        t_x_str = t_x.astype(str)
        t_fixed_str = t_fixed.astype(str)
        left = pd.DataFrame({"_t": t_x_str})
        right = pd.DataFrame({"_t": t_fixed_str, "_Pf": psource_f_raw.values}).drop_duplicates(subset=["_t"], keep="first")
        merged = left.merge(right, on="_t", how="left")
        psource_f_aligned = merged["_Pf"].values
    else:
        psource_f_aligned = np.full(len(psource_x), np.nan) if n_f != n_x else psource_f_raw.values
    out["Psource(f)"] = np.asarray(psource_f_aligned, dtype=float)
    out["Psource(x)"] = psource_x.values
    pf = np.asarray(out["Psource(f)"], dtype=float)
    px = np.asarray(out["Psource(x)"], dtype=float)
    # Minimum threshold: avoid unphysical Kt when Psource(f) is very small (IEC 61724 style)
    threshold = max(1.0, 0.01 * peak_power_kw * 1000.0)  # 1 W or 1% of nominal
    with np.errstate(divide="ignore", invalid="ignore"):
        kt = np.where(pf >= threshold, px / pf, 1.0)
    out["Kt"] = kt
    out["Ppv(x)"] = (ppv_series.values * kt).clip(min=0)

    # Ensure power/energy columns have no NaN (physical sense: NaN → 0)
    _sanitize_energy_output(out)
    return (out, "")


def _sanitize_energy_output(out: pd.DataFrame) -> None:
    """In-place: fill NaN with 0 for power/energy cols; clip to >= 0."""
    power_cols = ["Psource(f)", "Psource(x)", "Ppv(f)", "Ppv(x)"]
    for c in power_cols:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0).clip(lower=0)
    if "Kt" in out.columns:
        k = pd.to_numeric(out["Kt"], errors="coerce").fillna(1.0)
        out["Kt"] = np.clip(k.values, 0.0, 2.5)  # physically plausible cap (single-axis ~1.2–1.5)


def prepare_energy_table_data(
    result_df: pd.DataFrame,
    import_hourly_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Prepare energy result for table display: merge with import data, fill NaN→0 for
    power/energy/irradiance, ensure physical sense.
    """
    if result_df is None or result_df.empty:
        return result_df
    df = result_df.copy()

    # Add import columns (exact data from Step 1) not already in result
    if import_hourly_df is not None and not import_hourly_df.empty:
        for col in import_hourly_df.columns:
            if col not in df.columns:
                vals = import_hourly_df[col].values
                if len(vals) == len(df):
                    df[col] = vals

    # Columns where NaN → 0 (power, energy, irradiance)
    fill_zero_patterns = (
        "p", "electricity", "power", "source", "ppv", "epv", "esource",
        "g(i)", "g(h)", "gb", "gd", "gr", "irradiance", "ghi",
    )

    for col in df.columns:
        c = str(col).lower()
        if any(p in c for p in fill_zero_patterns):
            ser = pd.to_numeric(df[col], errors="coerce")
            if np.issubdtype(ser.dtype, np.number):
                df[col] = ser.fillna(0).clip(lower=0)

    # Renamed energy cols ( Epv, Esource )
    for col in ("Epv(f)", "Epv(x)", "Esource(f)", "Esource(x)"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0)

    return df
