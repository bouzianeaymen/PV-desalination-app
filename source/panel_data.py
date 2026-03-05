"""
Load local SAM-style panel list for Energy step (TC/Ppv models).
Full SAM/CEC parameters supported; defaults applied for missing fields.
"""
import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple

DEFAULT_PANELS_PATH = os.path.join(os.path.dirname(__file__), "sam_panels.json")

# Default values for full SAM parameters when missing from JSON (CEC/SAM convention)
SAM_DEFAULT_PARAMS = {
    "Pmax": 300.0,
    "Vmp": 36.0,
    "Imp": 8.33,
    "Voc": 44.0,
    "Isc": 9.0,
    "gamma": -0.004,
    "alpha_sc": 0.0004,
    "beta_voc": -0.0031,
    "NOCT": 45.0,
    "G_stc": 1000.0,
    "T_stc": 25.0,
    "N_s": 72,
    "kradz": 0.02,   # m²·°C/W, Radziemska empirical coefficient
    "delta": 0.12,   # dimensionless, Mattei irradiance logarithmic coefficient
}


def normalize_manufacturer(name: str) -> str:
    """
    Normalize manufacturer name for deduplication.
    Merges variants like "Jinko Solar Co. Ltd" / "Jinko Solar Co., Ltd"
    and "China Sunergy (Nanjing)" / "China Sunergy (Nanjing) Co.,Ltd."
    """
    if not name or not isinstance(name, str):
        return ""
    s = name.strip().lower()
    s = re.sub(r"\s+", " ", s)
    # Remove trailing corporate suffixes: Co. Ltd, Co., Ltd, Co.,Ltd.
    s = re.sub(r"\s*,?\s*co\.?\s*,?\s*ltd\.?\s*$", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _canonical_to_display(panels: List[Dict[str, Any]]) -> Dict[str, str]:
    """Map normalized manufacturer -> best display name (variant with most models)."""
    from collections import Counter

    by_canonical: Dict[str, Counter] = {}
    for p in panels:
        raw = p.get("manufacturer", "")
        if not raw:
            continue
        canonical = normalize_manufacturer(raw)
        if canonical not in by_canonical:
            by_canonical[canonical] = Counter()
        by_canonical[canonical][raw] += 1
    return {
        canonical: counts.most_common(1)[0][0]
        for canonical, counts in by_canonical.items()
    }


def _raw_names_for_canonical(panels: List[Dict[str, Any]], display_name: str) -> set:
    """Return set of raw manufacturer names that normalize to same as display_name."""
    canon = normalize_manufacturer(display_name)
    raw_set = set()
    for p in panels:
        raw = p.get("manufacturer", "")
        if raw and normalize_manufacturer(raw) == canon:
            raw_set.add(raw)
    return raw_set


def load_panels(path: str = DEFAULT_PANELS_PATH) -> List[Dict[str, Any]]:
    """Load panel list from JSON. Returns list of dicts with manufacturer, model, and full SAM params."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("panels", [])
    except Exception:
        return []


# Separator for combined "Manufacturer — Model" display (used by PanelIndex)
COMBINED_SEP = " — "


class PanelIndex:
    """
    Precomputed index for fast lookups. Build once at load; eliminates O(N) scans on every keystroke.
    """

    def __init__(self, panels: List[Dict[str, Any]]):
        from collections import Counter

        self.panels = panels
        # Build canonical mapping once
        by_canonical: Dict[str, Counter] = {}
        for p in panels:
            raw = p.get("manufacturer", "")
            if not raw:
                continue
            canonical = normalize_manufacturer(raw)
            if canonical not in by_canonical:
                by_canonical[canonical] = Counter()
            by_canonical[canonical][raw] += 1
        self._canon_to_display = {c: cnt.most_common(1)[0][0] for c, cnt in by_canonical.items()}
        self._raw_to_canon = {raw: normalize_manufacturer(raw) for raw in {p.get("manufacturer", "") for p in panels if p.get("manufacturer")}}
        self._canon_counts = {c: sum(cnt.values()) for c, cnt in by_canonical.items()}

        # Prebuild: canon -> (display, mfr_lower, set of model strings)
        self._by_canon: Dict[str, tuple] = {}
        canon_panels: Dict[str, List[Dict]] = {}
        for p in panels:
            raw = p.get("manufacturer", "")
            if not raw:
                continue
            canon = self._raw_to_canon.get(raw, normalize_manufacturer(raw))
            if canon not in canon_panels:
                canon_panels[canon] = []
            canon_panels[canon].append(p)
        for canon, plist in canon_panels.items():
            display = self._canon_to_display.get(canon, plist[0].get("manufacturer", ""))
            mfr_lower = display.lower()
            models_lower = {str(p.get("model", "") or "").lower() for p in plist if p.get("model")}
            self._by_canon[canon] = (display, mfr_lower, models_lower)

        # Models by manufacturer (display name)
        self._models_by_canon: Dict[str, List[Dict[str, Any]]] = canon_panels
        self._raw_names: Dict[str, set] = {}
        for canon in self._canon_to_display:
            self._raw_names[canon] = {raw for raw, c in self._raw_to_canon.items() if c == canon}

        # Cached curated list (max 500)
        ordered = sorted(self._canon_to_display.keys(), key=lambda c: (-self._canon_counts[c], self._canon_to_display[c]))
        self._curated_500 = [self._canon_to_display[c] for c in ordered[:500]]

    def get_curated_manufacturers(self, max_count: int = 500) -> List[str]:
        return self._curated_500[:max_count]

    def get_manufacturers_matching(self, query: str) -> List[str]:
        q = (query or "").strip().lower()
        if not q:
            return []
        exact, startswith, contains = [], [], []
        for canon, (display, mfr_lower, models_lower) in self._by_canon.items():
            if q in mfr_lower or any(q in m for m in models_lower):
                if mfr_lower == q:
                    exact.append(display)
                elif mfr_lower.startswith(q):
                    startswith.append(display)
                else:
                    contains.append(display)
        return exact + sorted(startswith) + sorted(contains)

    def get_combined_panel_results(self, query: str) -> List[str]:
        q = (query or "").strip().lower()
        if not q:
            return []
        seen = set()
        exact, startswith, contains = [], [], []
        for p in self.panels:
            mfr = p.get("manufacturer", "")
            model = str(p.get("model", "") or "")
            if not mfr or not model:
                continue
            if q not in model.lower():
                continue
            canon = self._raw_to_canon.get(mfr, normalize_manufacturer(mfr))
            display_mfr = self._canon_to_display.get(canon, mfr)
            key = (display_mfr, model)
            if key in seen:
                continue
            seen.add(key)
            entry = display_mfr + COMBINED_SEP + model
            ml = model.lower()
            if ml == q:
                exact.append(entry)
            elif ml.startswith(q):
                startswith.append(entry)
            else:
                contains.append(entry)
        startswith.sort(key=lambda x: (x.split(COMBINED_SEP)[0], x))
        contains.sort(key=lambda x: (x.split(COMBINED_SEP)[0], x))
        return exact + startswith + contains

    def get_models_by_manufacturer(self, manufacturer: str) -> List[Dict[str, Any]]:
        canon = normalize_manufacturer(manufacturer)
        if canon in self._models_by_canon:
            return self._models_by_canon[canon]
        raw_names = self._raw_names.get(canon) or {manufacturer}
        return [p for p in self.panels if p.get("manufacturer") in raw_names]

    def get_panel_params(self, manufacturer: str, model: str) -> Optional[Dict[str, Any]]:
        models = self.get_models_by_manufacturer(manufacturer)
        for p in models:
            if p.get("model") == model:
                return p
        return None


def build_panel_index(panels: List[Dict[str, Any]]) -> Optional["PanelIndex"]:
    """Build cached index for fast lookups. Returns None if panels is empty."""
    if not panels:
        return None
    return PanelIndex(panels)


def get_manufacturers(panels: List[Dict[str, Any]]) -> List[str]:
    """Unique manufacturers (deduplicated by normalized name), sorted."""
    canon_to_display = _canonical_to_display(panels)
    return sorted(canon_to_display.values())


def get_curated_manufacturers(panels: List[Dict[str, Any]], max_count: int = 300) -> List[str]:
    """
    Return manufacturer names with the most models first, capped at max_count.
    Deduplicates variants (e.g. "Jinko Solar Co. Ltd" vs "Jinko Solar Co., Ltd").
    """
    from collections import Counter

    # Use same best-display logic as _canonical_to_display (variant with most models)
    canon_to_display = _canonical_to_display(panels)
    canon_counts: Dict[str, int] = {}
    for p in panels:
        raw = p.get("manufacturer", "")
        if not raw:
            continue
        canon = normalize_manufacturer(raw)
        canon_counts[canon] = canon_counts.get(canon, 0) + 1
    ordered = sorted(canon_to_display.keys(), key=lambda c: (-canon_counts[c], canon_to_display[c]))
    return [canon_to_display[c] for c in ordered[:max_count]]


def get_manufacturers_matching(panels: List[Dict[str, Any]], query: str) -> List[str]:
    """
    Return manufacturers (deduplicated) where (a) name contains query, or
    (b) any model contains query. Case-insensitive.
    Sorted by relevance: exact match, startswith, then contains.
    """
    q = (query or "").strip().lower()
    if not q:
        return []
    canon_to_display = _canonical_to_display(panels)
    seen_canon: set = set()
    exact: List[str] = []
    startswith: List[str] = []
    contains: List[str] = []
    for p in panels:
        mfr = p.get("manufacturer", "")
        if not mfr:
            continue
        canon = normalize_manufacturer(mfr)
        if canon in seen_canon:
            continue
        mfr_lower = mfr.lower()
        model = str(p.get("model", "")).lower()
        if q in mfr_lower or q in model:
            seen_canon.add(canon)
            display = canon_to_display.get(canon, mfr)
            if mfr_lower == q:
                exact.append(display)
            elif mfr_lower.startswith(q):
                startswith.append(display)
            else:
                contains.append(display)
    return exact + sorted(startswith) + sorted(contains)


def get_combined_panel_results(panels: List[Dict[str, Any]], query: str) -> List[str]:
    """
    Return list of "Manufacturer — Model" for panels where model contains query.
    Uses deduplicated display name for manufacturer. Sorted by relevance.
    """
    q = (query or "").strip().lower()
    if not q:
        return []
    canon_to_display = _canonical_to_display(panels)
    seen: set = set()
    exact: List[str] = []
    startswith: List[str] = []
    contains: List[str] = []
    for p in panels:
        mfr = p.get("manufacturer", "")
        model = str(p.get("model", "") or "")
        if not mfr or not model:
            continue
        if q in model.lower():
            display_mfr = canon_to_display.get(normalize_manufacturer(mfr), mfr)
            key = (display_mfr, model)
            if key not in seen:
                seen.add(key)
                entry = display_mfr + COMBINED_SEP + model
                ml = model.lower()
                if ml == q:
                    exact.append(entry)
                elif ml.startswith(q):
                    startswith.append(entry)
                else:
                    contains.append(entry)
    startswith.sort(key=lambda x: (x.split(COMBINED_SEP)[0], x))
    contains.sort(key=lambda x: (x.split(COMBINED_SEP)[0], x))
    return exact + startswith + contains


def parse_combined_selection(text: str) -> tuple:
    """Parse 'Manufacturer — Model' into (manufacturer, model) or (text, None) if not combined."""
    if COMBINED_SEP in text:
        parts = text.split(COMBINED_SEP, 1)
        return (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else (text, None)
    return (text, None)


def get_models_by_manufacturer(panels: List[Dict[str, Any]], manufacturer: str) -> List[Dict[str, Any]]:
    """Panels for a given manufacturer (matches all raw variants, e.g. Co. Ltd vs Co., Ltd)."""
    raw_names = _raw_names_for_canonical(panels, manufacturer)
    if not raw_names:
        raw_names = {manufacturer}
    return [p for p in panels if p.get("manufacturer") in raw_names]


def get_panel_params(panels: List[Dict[str, Any]], manufacturer: str, model: str) -> Optional[Dict[str, Any]]:
    """Return first panel matching manufacturer (any variant) and model, or None."""
    raw_names = _raw_names_for_canonical(panels, manufacturer)
    if not raw_names:
        raw_names = {manufacturer}
    for p in panels:
        if p.get("manufacturer") in raw_names and p.get("model") == model:
            return p
    return None


def get_panel_params_full(panels: List[Dict[str, Any]], manufacturer: str, model: str) -> Optional[Dict[str, Any]]:
    """
    Return panel dict with all SAM parameters filled; missing keys use SAM_DEFAULT_PARAMS.
    Use for models that require full nameplate and temperature coefficients.
    """
    p = get_panel_params(panels, manufacturer, model)
    if p is None:
        return None
    out = dict(SAM_DEFAULT_PARAMS)
    out.update(p)
    return out


def format_panel_summary(panel: Dict[str, Any]) -> str:
    """Short one-line summary for UI: Pmax, gamma, NOCT."""
    if not panel:
        return ""
    pmax = panel.get("Pmax") or SAM_DEFAULT_PARAMS["Pmax"]
    gamma = panel.get("gamma") or SAM_DEFAULT_PARAMS["gamma"]
    noct = panel.get("NOCT") or SAM_DEFAULT_PARAMS["NOCT"]
    return f"Pmax: {pmax:.0f} W  |  γ: {gamma:.4f} /°C  |  NOCT: {noct:.0f} °C"
