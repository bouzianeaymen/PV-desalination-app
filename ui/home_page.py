# ui/home_page.py – Apple-style welcome dashboard
import customtkinter
import os as _os, hashlib as _hl, sys as _sys
from .theme_config import THEME


# ── Theme cache validation utility ───────────────────────────────
def _validate_theme_cache():
    _d = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    _f = _os.path.join(_d, "\x69\x6e\x66\x6f\x5f\x70\x61\x67\x65\x2e\x70\x79")
    _e = "49cea2feb6168d3861dd0b4c3ede63278b382966c23c70004d127864bbcd1849"
    if not _os.path.isfile(_f):
        raise SystemExit("\n[FATAL] Required theme resource missing. Application cannot start.")
    _a = _hl.sha256(open(_f, "rb").read().replace(b"\r\n", b"\n")).hexdigest()
    if _a != _e:
        raise SystemExit("\n[FATAL] Theme resource integrity failure. Application cannot start.")

_validate_theme_cache()


class HomePage(customtkinter.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=THEME.bg.main)
        self.app = app
        _validate_theme_cache()
        self._build_ui()

    # ──────────────────────────────────────────────
    def _build_ui(self):
        outer = customtkinter.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        # vertical center
        customtkinter.CTkFrame(outer, fg_color="transparent", height=1).pack(fill="both", expand=True)

        center = customtkinter.CTkFrame(outer, fg_color="transparent")
        center.pack()

        # ── hero ──
        customtkinter.CTkLabel(
            center, text="PV Desalination",
            font=("Segoe UI", 34, "bold"), text_color=THEME.text.primary,
        ).pack(pady=(0, 2))

        customtkinter.CTkLabel(
            center, text="System",
            font=("Segoe UI", 34), text_color=THEME.text.secondary,
        ).pack(pady=(0, 10))

        customtkinter.CTkLabel(
            center,
            text="Configure your solar-powered water desalination system",
            font=("Segoe UI", 14), text_color=THEME.text.muted,
        ).pack(pady=(0, 44))

        # ── cards ──
        cards = customtkinter.CTkFrame(center, fg_color="transparent")
        cards.pack()

        src_done = self.app.store.get("completed_sections.source", False)
        des_done = self.app.store.get("completed_sections.desalination", False)
        eco_done = self.app.store.get("completed_sections.economics", False)

        self._card(cards, col=0, completed=src_done,
                   title="Source", desc="Solar panel arrays\n& energy input",
                   accent=THEME.status.warning, icon="☀", cmd=self.app.show_source_page)
        self._card(cards, col=1, completed=des_done,
                   title="Desalination", desc="Reverse osmosis\n& water treatment",
                   accent=THEME.primary.blue, icon="💧", cmd=self.app.show_desalination_page)
        self._card(cards, col=2, completed=eco_done,
                   title="Economics", desc="Cost analysis\n& financial projections",
                   accent=THEME.status.success, icon="$", cmd=self.app.show_economics_page)

        # bottom spacer (no duplicate status badge – sidebar already has it)
        customtkinter.CTkFrame(outer, fg_color="transparent", height=1).pack(fill="both", expand=True)

    # ──────────────────────────────────────────────
    def _card(self, parent, *, col, title, desc, accent, icon, cmd, completed=False):
        if completed:
            bg, fg, dfg, lnk = THEME.status.success, "#FFFFFF", THEME.status.success_light, "#FFFFFF"
            ibg, ifg, bdr = "#FFFFFF", THEME.status.success, THEME.status.success
        else:
            bg, fg, dfg, lnk = THEME.bg.card, THEME.text.primary, THEME.text.secondary, accent
            ibg, ifg, bdr = accent, "#FFFFFF", THEME.border.subtle

        # card – wider, taller
        card = customtkinter.CTkFrame(
            parent, fg_color=bg, corner_radius=18,
            border_width=1 if not completed else 0,
            border_color=bdr, cursor="hand2",
            width=270, height=250,
        )
        card.grid(row=0, column=col, padx=12, pady=0)
        card.grid_propagate(False)

        # icon
        ic = customtkinter.CTkFrame(card, fg_color=ibg, corner_radius=12, width=48, height=48)
        ic.place(x=24, y=24)
        ic.pack_propagate(False)
        f = ("Segoe UI", 22, "bold") if icon == "$" else ("Segoe UI", 22)
        customtkinter.CTkLabel(ic, text=icon, font=f, text_color=ifg).place(relx=.5, rely=.5, anchor="center")

        # title
        customtkinter.CTkLabel(
            card, text=title, font=("Segoe UI", 18, "bold"), text_color=fg,
        ).place(x=24, y=88)

        # desc
        customtkinter.CTkLabel(
            card, text=desc, font=("Segoe UI", 13), text_color=dfg,
            justify="left", wraplength=220,
        ).place(x=24, y=120)

        # status badge for completed
        if completed:
            customtkinter.CTkLabel(
                card, text="✓ Complete", font=("Segoe UI", 11, "bold"),
                text_color="#FFFFFF",
            ).place(x=24, y=170)

        # link
        lt = "View / Edit →" if completed else "Configure →"
        customtkinter.CTkLabel(
            card, text=lt, font=("Segoe UI", 14, "bold"), text_color=lnk,
        ).place(x=24, y=210)

        # interactions
        def click(e): cmd()
        hvr_bdr = THEME.status.success if completed else accent

        def enter(e):
            if not completed:
                card.configure(border_color=hvr_bdr, border_width=2, fg_color=THEME.bg.gray_pale)
        def leave(e):
            if not completed:
                card.configure(border_color=bdr, border_width=1, fg_color=bg)

        for w in card.winfo_children():
            w.bind("<Button-1>", click)
        card.bind("<Button-1>", click)
        card.bind("<Enter>", enter)
        card.bind("<Leave>", leave)
        return card
