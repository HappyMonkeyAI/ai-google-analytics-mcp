#!/usr/bin/env python3
"""Scan ~/projects for .ga4.config.json and print a markdown inventory table."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_ROOTS = [Path.home() / "projects"]
MAX_DEPTH = 4


def scan_roots(roots: list[Path], *, max_depth: int = MAX_DEPTH) -> list[dict]:
    rows: list[dict] = []
    for root in roots:
        if not root.is_dir():
            continue
        root_str = str(root)
        for dirpath, dirnames, filenames in os.walk(root_str):
            depth = dirpath[len(root_str) :].count(os.sep)
            if depth >= max_depth:
                dirnames.clear()
                continue
            dirnames[:] = [
                d
                for d in dirnames
                if d not in (".git", "node_modules", ".venv", "venv", "__pycache__")
            ]
            if ".ga4.config.json" not in filenames:
                continue
            cfg = Path(dirpath) / ".ga4.config.json"
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
            rows.append(
                {
                    "config_path": str(cfg),
                    "project_dir": str(cfg.parent),
                    "measurement_id": data.get("measurement_id", ""),
                    "property_id": data.get("property_id", ""),
                    "website_url": data.get("website_url", ""),
                    "stream_name": data.get("stream_name", ""),
                }
            )
    rows.sort(key=lambda r: r["project_dir"])
    return rows


def to_markdown(rows: list[dict]) -> str:
    lines = [
        "# GA4 project inventory (generated)",
        "",
        "| Project dir | Website | Measurement ID | Property ID | Stream | Config |",
        "|-------------|---------|----------------|-------------|--------|--------|",
    ]
    if not rows:
        lines.append("| *(none found)* | | | | | |")
    else:
        for r in rows:
            lines.append(
                f"| `{r['project_dir']}` | {r['website_url']} | `{r['measurement_id']}` | "
                f"`{r['property_id']}` | {r['stream_name']} | `{r['config_path']}` |"
            )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    roots = [Path(p) for p in argv[1:]] if len(argv) > 1 else DEFAULT_ROOTS
    print(to_markdown(scan_roots(roots)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))