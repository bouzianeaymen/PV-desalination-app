# ui/source/equation_renderer.py
# Renders TC and Ppv equations as LaTeX/mathtext for display in Step 2 Energy UI

import io
from typing import Optional, Tuple, Dict, Any, List

# LaTeX strings for TC models (matplotlib mathtext format)
TC_LATEX = {
    "NOCT-style": r"$T_c = T_a + (NOCT - 20) \times \frac{G}{800}$",
    "Modèle N°2": r"$T_c = T_a + \frac{G}{U_0 + U_1 \times V_v}$",
    "Modèle N°3": r"$T_c = T_a + \frac{T_{NOCT}-20}{800 + h\,\frac{V_v-V_0}{V_0}(T_{NOCT}-20)} \times G$"
    + "\n" + r"$\quad h = 3.8\,V_v + 5.7$",
}

# LaTeX strings for Ppv models
PPV_LATEX = {
    "Standard": r"$P_{out} = P_{nom} \times \frac{G}{G_{stc}} \times \left[1 + \gamma_p (T_c - T_{ref})\right]$",
    "Radziemska": r"$P_{out} = P_{nom} \times \frac{G}{G_{stc}} \times \left[1 + \gamma_p (T_a + k_{radz} G - T_{ref})\right]$",
    "Mattei": r"$P_{out} = P_{nom} \times \frac{G}{G_{stc}} \times \left[1 + \gamma_p(T_c-T_{ref}) + \delta \ln\frac{G}{G_{stc}}\right]$",
}


def render_equations_to_image(
    tc_latex: Optional[str],
    ppv_latex: Optional[str],
    width_inches: float = 6.5,
    dpi: int = 150,
    bg_color: str = "#F5F5F5",
    fontsize: int = 18,
) -> Optional[Tuple[Any, Tuple[int, int]]]:
    """Render LaTeX equations to PIL Image. Returns (Image, (width, height)) or None on failure."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from PIL import Image
    except ImportError:
        return None

    if not tc_latex and not ppv_latex:
        return None

    plt.rcParams["mathtext.fontset"] = "stix"
    plt.rcParams["axes.unicode_minus"] = False

    fig_h = 2.5 if (tc_latex and ppv_latex) else 1.5
    fig, ax = plt.subplots(figsize=(width_inches, fig_h), dpi=dpi)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    x_left = 0.02
    y_pos = 0.98
    label_fs = 10
    eq_fs = fontsize
    text_color = "#0d0d0d"
    gap_between_sections = 0.22

    if tc_latex:
        ax.text(x_left, y_pos, "Cell temperature $T_c$", fontsize=label_fs, color="#444", ha="left", va="top", transform=ax.transAxes)
        y_pos -= 0.07
        tc_lines = tc_latex.split("\n")
        line_height = 0.14
        line_gap = 0.16
        for i, line in enumerate(tc_lines):
            line = line.strip()
            if line:
                ax.text(x_left, y_pos, line, fontsize=eq_fs, fontweight="medium", color=text_color, ha="left", va="top", transform=ax.transAxes)
            y_pos -= line_height
            if i < len(tc_lines) - 1:
                y_pos -= line_gap
        y_pos -= gap_between_sections

    if ppv_latex:
        ax.text(x_left, y_pos, "Output power $P_{out}$", fontsize=label_fs, color="#444", ha="left", va="top", transform=ax.transAxes)
        y_pos -= 0.07
        ax.text(x_left, y_pos, ppv_latex, fontsize=eq_fs, fontweight="medium", color=text_color, ha="left", va="top", transform=ax.transAxes)

    plt.tight_layout(pad=0.3)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", facecolor=fig.get_facecolor(), edgecolor="none", bbox_inches="tight", pad_inches=0.15, dpi=dpi)
    plt.close(fig)
    buf.seek(0)

    try:
        img = Image.open(buf).convert("RGBA")
        return (img, (img.width, img.height))
    except Exception:
        return None


# Unit for display (empty = dimensionless)
CONST_UNITS = {
    "NOCT": "°C", "TNOCT": "°C", "Tref": "°C",
    "U_0": "W/(m²·K)", "U_1": "W/(m²·K·m/s)",
    "V0": "m/s", "Pnom": "W", "G_stc": "W/m²",
    "gamma": "/°C", "γp": "/°C", "kradz": "m²·°C/W", "δ": "",
}


def get_constant_value(
    const_name: str,
    panel: Dict[str, Any],
    peak_power_kw: float = 1.0,
    defaults: Optional[Dict[str, Any]] = None,
) -> str:
    """Map constant name to panel key and return formatted value string."""
    if defaults is None:
        defaults = {
            "NOCT": 45.0, "U_0": 25.0, "U_1": 6.84, "V0": 1.0,
            "G_stc": 1000.0, "T_stc": 25.0, "gamma": -0.004,
            "kradz": 0.02, "delta": 0.12, "Pmax": 300.0,
        }
    mapping = {
        "NOCT": ("NOCT", ".1f"),
        "TNOCT": ("NOCT", ".1f"),
        "U_0": ("U_0", ".2f"),
        "U_1": ("U_1", ".2f"),
        "V0": ("V0", ".2f"),
        "Pnom": ("_derived", None),
        "G_stc": ("G_stc", ".0f"),
        "γp": ("gamma", ".4f"),
        "Tref": ("T_stc", ".1f"),
        "kradz": ("kradz", ".3f"),
        "δ": ("delta", ".3f"),
    }
    entry = mapping.get(const_name)
    if not entry:
        return str(panel.get(const_name, defaults.get(const_name, "—")))
    key, fmt = entry
    if key == "_derived":
        val = peak_power_kw * 1000.0
        return f"{val:.0f}"
    val = panel.get(key, defaults.get(key))
    if val is None:
        return "—"
    try:
        v = float(val)
        return f"{v:{fmt}}" if fmt else str(v)
    except (TypeError, ValueError):
        return str(val)


def format_constants_card(
    tc_constants: List[str],
    ppv_constants: List[str],
    panel: Optional[Dict[str, Any]],
    peak_power_kw: float = 1.0,
) -> str:
    """Format constants and their values for the constants card (two-column, units)."""
    if not panel:
        return "Select a panel to see constants."
    lines = []
    seen = set()
    name_w = 8
    val_w = 10
    for c in tc_constants + ppv_constants:
        if c in seen:
            continue
        seen.add(c)
        val = get_constant_value(c, panel, peak_power_kw)
        unit = CONST_UNITS.get(c, "")
        val_str = f"{val} {unit}".strip() if unit else val
        name_fmt = c.ljust(name_w)
        val_fmt = val_str.rjust(val_w)
        lines.append(f"{name_fmt}  {val_fmt}")
    return "\n".join(lines) if lines else "—"
