"""Roost house style for matplotlib figures — import, don't copy.

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "figures"))
    from style import apply_style, C, panel_label, source_line

Design tokens + conventions defined in docs/FIGURE_DESIGN.md.
"""
from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt

# ---- color tokens (docs/FIGURE_DESIGN.md §3) ---------------------------
C = {
    "ink": "#0f172a",
    "muted": "#475569",
    "faint": "#94a3b8",
    "surface": "#f8fafc",
    "card": "#ffffff",
    "primary": "#1d4ed8",
    "primary_soft": "#bfdbfe",
    "primary_bg": "#eff6ff",
    "alert": "#dc2626",
    "alert_soft": "#fee2e2",
    "alert_bg": "#fef2f2",
    "caution": "#d97706",
    "caution_soft": "#fef3c7",
    "caution_bg": "#fffbeb",
    "good": "#16a34a",
    "good_soft": "#dcfce7",
    "good_bg": "#f0fdf4",
    # dedicated genomics-stream hue (Fig 1+ convention: genomics is a data
    # stream, not a positive outcome — never reuse "good" for it)
    "genomics": "#0f766e",
    "genomics_soft": "#99f6e4",
    "genomics_bg": "#f0fdfa",
    # neutral stream (surveillance track)
    "neutral": "#475569",
    "neutral_bg": "#f1f5f9",
}

_APPLIED = False


def apply_style() -> None:
    """Set rcParams to the house style (idempotent)."""
    global _APPLIED
    if _APPLIED:
        return
    matplotlib.use("Agg")
    plt.rcParams.update({
        # typography (FIGURE_DESIGN §2)
        "font.family": "Lato",
        "font.size": 12.5,
        "figure.titlesize": 30,
        "figure.titleweight": "bold",
        "axes.titlesize": 13.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 12.5,
        "axes.labelcolor": C["muted"],
        "xtick.labelsize": 11.5,
        "ytick.labelsize": 11.5,
        "xtick.color": C["muted"],
        "ytick.color": C["muted"],
        "legend.fontsize": 11,
        # layout (§4)
        "figure.facecolor": C["surface"],
        "axes.facecolor": C["card"],
        "axes.edgecolor": "#cbd5e1",
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": "#e2e8f0",
        "grid.linewidth": 0.7,
        "axes.axisbelow": True,
        # bars/lines
        "patch.linewidth": 0.6,
        "patch.edgecolor": C["ink"],
        "lines.solid_capstyle": "round",
        # export
        "savefig.facecolor": C["surface"],
        "savefig.dpi": 160,
    })
    _APPLIED = True


def panel_label(ax, letter: str, title: str, pad: float = 10) -> None:
    """Bold 'A ·' panel label + regular title, top-left (§2)."""
    ax.set_title(f"{letter} · {title}", loc="left", pad=pad,
                 fontsize=13.5, fontweight="bold", color=C["ink"])


def source_line(fig, text: str) -> None:
    """Bottom-left source/footnote line in faint slate (§5)."""
    fig.text(0.008, 0.004, text, fontsize=10, color=C["faint"])


def big_number(ax, x, y, value: str, color: str, size: int = 64,
               ha: str = "center", weight: str = "black") -> None:
    """Display number in Lato Black (§2)."""
    ax.text(x, y, value, fontsize=size, fontweight=weight, color=color,
            ha=ha, va="center")


def save(fig, name: str, root) -> None:
    """Standard export set: preview 1600-class + svg/pdf/png at export size."""
    from pathlib import Path
    preview = Path(root) / "figures" / "preview" / f"{name}.png"
    export = Path(root) / "figures" / "export"
    preview.parent.mkdir(parents=True, exist_ok=True)
    export.mkdir(parents=True, exist_ok=True)
    fig.savefig(preview, bbox_inches="tight", facecolor=C["surface"])
    for ext in ("png", "svg", "pdf"):
        fig.savefig(export / f"{name}.{ext}", bbox_inches="tight",
                    facecolor=C["surface"])
    print(f"wrote figures/preview/{name}.png + export/{{png,svg,pdf}}")
