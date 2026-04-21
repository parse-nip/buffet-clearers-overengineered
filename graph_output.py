"""Optional graph export when BUFFET_GRAPH_ROOT is set (used by run_graphs.py)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def export_root() -> Optional[Path]:
    raw = os.environ.get("BUFFET_GRAPH_ROOT")
    return Path(raw).resolve() if raw else None


def save_graph(
    fig,
    category: str,
    filename: str,
    *,
    dpi: int = 130,
    facecolor=None,
    **kwargs,
) -> Optional[Path]:
    root = export_root()
    if root is None:
        return None
    out_dir = root / category
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    kw: dict = {"dpi": dpi, "bbox_inches": "tight"}
    if facecolor is not None:
        kw["facecolor"] = facecolor
    kw.update(kwargs)
    fig.savefig(path, **kw)
    return path


def save_and_close_if_exporting(fig, category: str, filename: str, **save_kw) -> bool:
    import matplotlib.pyplot as plt

    path = save_graph(fig, category, filename, **save_kw)
    if path:
        plt.close(fig)
        return True
    return False


def save_export_or_interactive(
    fig,
    category: str,
    filename: str,
    *,
    facecolor=None,
    dpi: int = 130,
) -> None:
    import matplotlib.pyplot as plt

    path = save_graph(fig, category, filename, dpi=dpi, facecolor=facecolor)
    if path:
        plt.close(fig)
    else:
        plt.savefig(filename, dpi=dpi, facecolor=facecolor, bbox_inches="tight")
        plt.show()
