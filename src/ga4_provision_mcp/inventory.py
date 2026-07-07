"""Filesystem and registry inventory for GA4 provisioning gaps."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

PathLike = Union[str, Path]

from ga4_provision_mcp.integrations import (
    GA4_CONFIG_NAME,
    _guess_web_roots,
    _load_registry,
    launcher_status,
    read_ga4_config,
)

DEFAULT_SCAN_ROOTS = [Path.home() / "projects"]
SKIP_DIR_NAMES = frozenset({".git", "node_modules", ".venv", "venv", "__pycache__"})
DEFAULT_MAX_DEPTH = 4


def _walk_ga4_config_rows(root: Path, max_depth: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    root_str = str(root.resolve())
    for dirpath, dirnames, filenames in os.walk(root_str):
        depth = dirpath[len(root_str) :].count(os.sep)
        if depth >= max_depth:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        if GA4_CONFIG_NAME not in filenames:
            continue
        cfg = Path(dirpath) / GA4_CONFIG_NAME
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            data = {"_parse_error": str(exc)}
        rows.append(
            {
                "config_path": str(cfg),
                "project_dir": str(cfg.parent),
                "measurement_id": data.get("measurement_id", ""),
                "property_id": data.get("property_id", ""),
                "website_url": data.get("website_url", ""),
                "stream_name": data.get("stream_name", ""),
                "valid": "_parse_error" not in data,
            }
        )
    return rows


def scan_local_ga4_configs(
    roots: Optional[Iterable[PathLike]] = None,
    *,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> Dict[str, Any]:
    """Walk roots for `.ga4.config.json` and return structured rows."""
    root_paths = [Path(p).expanduser() for p in (roots or DEFAULT_SCAN_ROOTS)]
    rows: List[Dict[str, Any]] = []
    for root in root_paths:
        if not root.is_dir():
            continue
        rows.extend(_walk_ga4_config_rows(root, max_depth))
    rows.sort(key=lambda r: r["project_dir"])
    return {"ok": True, "count": len(rows), "roots": [str(p) for p in root_paths], "configs": rows}


def _collect_tracking_candidates(
    base: Path,
    layouts: List[str],
    html_candidates: List[str],
) -> None:
    for rel in ("src/app/layout.tsx", "app/layout.tsx", "public/index.html", "index.html"):
        p = base / rel
        if not p.is_file():
            continue
        target = layouts if rel.endswith("layout.tsx") else html_candidates
        target.append(str(p))


def _tracking_search_bases(root: Path) -> List[str]:
    web_roots = _guess_web_roots(root)
    search_bases = list(web_roots)
    if str(root) not in search_bases:
        search_bases.append(str(root))
    return search_bases


def detect_tracking_stack(project_dir: str | Path) -> Dict[str, Any]:
    """Heuristic: Next.js App Router vs static HTML entrypoints."""
    root = Path(project_dir).expanduser().resolve()
    if not root.is_dir():
        return {"ok": False, "error": f"Not a directory: {root}"}

    layouts: List[str] = []
    html_candidates: List[str] = []
    search_bases = _tracking_search_bases(root)
    for wr in search_bases:
        _collect_tracking_candidates(Path(wr), layouts, html_candidates)

    if layouts:
        mode = "nextjs"
    elif html_candidates:
        mode = "html"
    else:
        mode = "unknown"

    return {
        "ok": True,
        "project_dir": str(root),
        "recommended_mode": mode,
        "suggested_web_roots": _guess_web_roots(root),
        "layout_paths": layouts,
        "html_paths": html_candidates,
    }


def _matches_filter_query(project: Dict[str, Any], q: str) -> bool:
    return (
        q in (project.get("name") or "").lower()
        or q in (project.get("slug") or "").lower()
        or q in (project.get("summary") or "").lower()
        or any(q in t.lower() for t in project.get("tech_stack") or [])
        or q in (project.get("url") or "").lower()
    )


def _project_gap_row(project: Dict[str, Any], *, include_partial: bool) -> Optional[Dict[str, Any]]:
    path_str = (project.get("path") or "").strip()
    registry_ga4 = (project.get("analytics") or {}).get("ga4") or {}
    local = read_ga4_config(path_str) if path_str else {"found": False}
    has_local = local.get("found") is True
    has_registry = bool(registry_ga4.get("measurement_id"))
    if has_local and has_registry:
        return None
    if not include_partial and (has_local or has_registry):
        return None
    row = {
        "slug": project.get("slug"),
        "name": project.get("name"),
        "path": path_str,
        "url": project.get("url"),
        "has_local_ga4_config": has_local,
        "has_registry_ga4": has_registry,
        "gap": "missing_both" if not has_local and not has_registry else "partial",
    }
    if path_str:
        row["tracking_stack"] = detect_tracking_stack(path_str)
    return row


def list_projects_needing_ga4(
    filter_query: str = "",
    limit: int = 50,
    *,
    include_partial: bool = True,
) -> Dict[str, Any]:
    """
    Registry projects missing GA4 wiring (no `.ga4.config.json` and no registry analytics.ga4).
    When registry env is unset, returns ok=false with reason.
    """
    st = launcher_status()
    if not st.get("available"):
        return {
            "ok": False,
            "launcher": st,
            "count": 0,
            "projects": [],
            "reason": st.get("reason", "launcher registry unavailable"),
        }

    data = _load_registry()
    projects: List[Dict[str, Any]] = list(data.get("projects") or [])
    if filter_query:
        q = filter_query.lower()
        projects = [p for p in projects if _matches_filter_query(p, q)]

    gaps: List[Dict[str, Any]] = []
    for p in projects[: max(1, min(limit, 100))]:
        row = _project_gap_row(p, include_partial=include_partial)
        if row is None:
            continue
        gaps.append(row)

    return {
        "ok": True,
        "launcher": st,
        "count": len(gaps),
        "projects": gaps,
    }


def inventory_markdown_table(rows: List[Dict[str, Any]]) -> str:
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
                f"| `{r['project_dir']}` | {r.get('website_url', '')} | "
                f"`{r.get('measurement_id', '')}` | `{r.get('property_id', '')}` | "
                f"{r.get('stream_name', '')} | `{r.get('config_path', '')}` |"
            )
    lines.append("")
    return "\n".join(lines)
