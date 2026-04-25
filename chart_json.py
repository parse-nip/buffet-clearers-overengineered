"""Write interactive chart specs next to PNG exports (under BUFFET_GRAPH_ROOT/data/...)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from graph_output import export_root


def _sanitize(obj: Any) -> Any:
    if obj is None or isinstance(obj, str):
        return obj
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.integer, np.floating)):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, np.ndarray):
        return _sanitize(obj.tolist())
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, int) and not isinstance(obj, bool):
        return obj
    try:
        return float(obj)
    except (TypeError, ValueError):
        return str(obj)


def write_chart_spec(category: str, filename_png: str, spec: dict[str, Any]) -> Path | None:
    root = export_root()
    if root is None:
        return None
    stem = Path(filename_png).stem
    out_dir = root / "data" / category
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stem}.json"
    clean = _sanitize(spec)
    path.write_text(
        json.dumps(clean, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    return path
