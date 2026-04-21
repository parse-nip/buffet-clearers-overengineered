#!/usr/bin/env python3
"""Load data, build features, render matplotlib figures into ./out/ (by category)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Non-interactive backend before any script imports pyplot
import matplotlib

matplotlib.use("Agg")


def _ensure_utf8_stdio() -> None:
    """Avoid UnicodeEncodeError on Windows (cp1252) when scripts print emoji/arrows."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT_DIR = ROOT / "out"
# Mirror PNGs here so README images can be committed: many global .gitignore files ignore `out/`
# (e.g. Next.js), which hides ./out from Git and breaks README previews on GitHub.
README_DOCS = ROOT / "docs" / "readme"

# Organized subfolders (food_patterns, weekly_alerts, prediction_model)
os.environ["BUFFET_GRAPH_ROOT"] = str(OUT_DIR)


def main() -> int:
    _ensure_utf8_stdio()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ("food_patterns", "weekly_alerts", "prediction_model"):
        (OUT_DIR / sub).mkdir(parents=True, exist_ok=True)

    ns: dict = {"__name__": "__main__"}
    steps = (
        "load_inspect.py",
        "feature_extract.py",
        "food_pattern.py",
        "weekly_alert.py",
        "prediction_model.py",
    )
    for script_name in steps:
        path = SRC / script_name
        if not path.is_file():
            print(f"Missing {path}", file=sys.stderr)
            return 1
        ns["__file__"] = str(path)
        code = path.read_text(encoding="utf-8")
        exec(compile(code, str(path), "exec"), ns)

    graphs = sorted(
        str(p.relative_to(OUT_DIR)).replace("\\", "/")
        for p in OUT_DIR.rglob("*.png")
    )
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_root": str(OUT_DIR),
        "graphs": graphs,
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    for png in OUT_DIR.rglob("*.png"):
        rel = png.relative_to(OUT_DIR)
        dest = README_DOCS / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(png, dest)
    print(f"Wrote {len(graphs)} graph(s) under {OUT_DIR}")
    print(f"Manifest: {OUT_DIR / 'manifest.json'}")
    print(f"README gallery mirror: {README_DOCS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
