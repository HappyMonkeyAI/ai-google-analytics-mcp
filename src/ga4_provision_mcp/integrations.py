"""Optional hooks to launcher project registry and per-repo Keymaster context.

All integrations are opt-in via environment variables. When unset or missing,
callers receive structured unavailable responses — no imports from sibling repos.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

GA4_CONFIG_NAME = ".ga4.config.json"
KEYMASTER_DIR = ".keymaster"
BOOTSTRAP_KEY_FILE = "project.key"


def _env_path(*names: str) -> Optional[Path]:
    for name in names:
        raw = os.environ.get(name, "").strip()
        if raw:
            p = Path(raw).expanduser()
            return p
    return None


def launcher_registry_path() -> Optional[Path]:
    return _env_path("GA4_LAUNCHER_REGISTRY_JSON", "LAUNCHER_REGISTRY_JSON")


def launcher_registry_writable() -> bool:
    return os.environ.get("GA4_LAUNCHER_REGISTRY_WRITABLE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def launcher_status() -> Dict[str, Any]:
    path = launcher_registry_path()
    if not path:
        return {
            "available": False,
            "reason": "Set GA4_LAUNCHER_REGISTRY_JSON (or LAUNCHER_REGISTRY_JSON) to enable.",
        }
    if not path.is_file():
        return {
            "available": False,
            "path": str(path),
            "reason": "Registry file not found.",
        }
    return {
        "available": True,
        "path": str(path),
        "writable": launcher_registry_writable(),
    }


def _load_registry() -> Dict[str, Any]:
    path = launcher_registry_path()
    if not path or not path.is_file():
        raise FileNotFoundError("launcher registry not configured or missing")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_registry(data: Dict[str, Any]) -> None:
    if not launcher_registry_writable():
        raise PermissionError(
            "Registry writes disabled. Set GA4_LAUNCHER_REGISTRY_WRITABLE=true to allow annotate."
        )
    path = launcher_registry_path()
    if not path:
        raise FileNotFoundError("launcher registry path not set")
    data["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def read_ga4_config(project_dir: str | Path) -> Dict[str, Any]:
    root = Path(project_dir).expanduser().resolve()
    cfg = root / GA4_CONFIG_NAME
    if not cfg.is_file():
        return {"found": False, "path": str(cfg)}
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"found": False, "path": str(cfg), "error": f"invalid json: {exc}"}
    return {"found": True, "path": str(cfg), "config": data}


def _guess_web_roots(project_path: Path) -> List[str]:
    candidates = [
        project_path / "web",
        project_path,
    ]
    out: List[str] = []
    for c in candidates:
        if (c / "package.json").is_file():
            out.append(str(c))
        if (c / "src" / "app" / "layout.tsx").is_file():
            out.append(str(c))
    # dedupe preserve order
    seen: set[str] = set()
    unique: List[str] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _project_row_enriched(project: Dict[str, Any]) -> Dict[str, Any]:
    path_str = (project.get("path") or "").strip()
    row = dict(project)
    row["ga4_config"] = None
    row["keymaster"] = {"available": False}
    if path_str:
        ga4 = read_ga4_config(path_str)
        if ga4.get("found"):
            row["ga4_config"] = ga4
        row["keymaster"] = keymaster_bootstrap_at(path_str)
        row["suggested_web_roots"] = _guess_web_roots(Path(path_str))
    url = (project.get("url") or "").strip()
    if url and not row.get("suggested_website_url"):
        row["suggested_website_url"] = url
    ga4_meta = (project.get("analytics") or {}).get("ga4") or {}
    if ga4_meta:
        row["registry_ga4"] = ga4_meta
    return row


def list_launcher_projects(filter_query: str = "", limit: int = 50) -> Dict[str, Any]:
    st = launcher_status()
    if not st.get("available"):
        return {"ok": False, "launcher": st, "projects": [], "count": 0}
    data = _load_registry()
    projects: List[Dict[str, Any]] = list(data.get("projects") or [])
    if filter_query:
        q = filter_query.lower()
        projects = [
            p
            for p in projects
            if q in (p.get("name") or "").lower()
            or q in (p.get("slug") or "").lower()
            or q in (p.get("summary") or "").lower()
            or any(q in t.lower() for t in p.get("tech_stack") or [])
            or q in (p.get("url") or "").lower()
        ]
    projects = projects[: max(1, min(limit, 100))]
    enriched = [_project_row_enriched(p) for p in projects]
    return {
        "ok": True,
        "launcher": st,
        "count": len(enriched),
        "projects": enriched,
    }


def get_launcher_project(slug: str) -> Dict[str, Any]:
    st = launcher_status()
    if not st.get("available"):
        return {"ok": False, "launcher": st, "found": False}
    slug = slug.strip()
    data = _load_registry()
    for p in data.get("projects") or []:
        if p.get("slug") == slug:
            return {"ok": True, "launcher": st, "found": True, "project": _project_row_enriched(p)}
    return {"ok": True, "launcher": st, "found": False, "error": f"slug not found: {slug}"}


def resolve_project_for_ga4(
    *,
    slug: str = "",
    project_dir: str = "",
) -> Dict[str, Any]:
    """Resolve slug and/or filesystem path for GA4 provisioning hints."""
    if not slug.strip() and not project_dir.strip():
        return {"ok": False, "error": "Provide registry slug and/or project_dir"}

    result: Dict[str, Any] = {"ok": True, "launcher": launcher_status(), "keymaster": {}}

    if project_dir.strip():
        root = Path(project_dir).expanduser().resolve()
        result["project_dir"] = str(root)
        result["ga4_config"] = read_ga4_config(root)
        result["keymaster"] = keymaster_bootstrap_at(root)
        result["suggested_web_roots"] = _guess_web_roots(root)

    if slug.strip():
        lp = get_launcher_project(slug)
        result["registry"] = lp
        if lp.get("found") and lp.get("project"):
            proj = lp["project"]
            if not result.get("project_dir") and proj.get("path"):
                result["project_dir"] = proj["path"]
                result["ga4_config"] = read_ga4_config(proj["path"])
                result["keymaster"] = keymaster_bootstrap_at(proj["path"])
                result["suggested_web_roots"] = _guess_web_roots(Path(proj["path"]))
            if proj.get("suggested_website_url"):
                result["suggested_website_url"] = proj["suggested_website_url"]
            elif proj.get("url"):
                result["suggested_website_url"] = proj["url"]

    if not result.get("suggested_website_url") and result.get("ga4_config", {}).get("found"):
        cfg = result["ga4_config"].get("config") or {}
        if cfg.get("website_url"):
            result["suggested_website_url"] = cfg["website_url"]

    result["agent_hints"] = build_agent_integration_hints(result)
    return result


def sync_ga4_to_launcher_registry(
    slug: str,
    measurement_id: str,
    property_id: str,
    website_url: str = "",
    stream_name: str = "",
) -> Dict[str, Any]:
    """Merge GA4 metadata into a registry project (optional write)."""
    st = launcher_status()
    if not st.get("available"):
        return {"ok": False, "launcher": st, "error": "launcher registry unavailable"}
    if not st.get("writable"):
        return {
            "ok": False,
            "launcher": st,
            "error": "Registry read-only. Set GA4_LAUNCHER_REGISTRY_WRITABLE=true to sync.",
        }
    mid = measurement_id.strip()
    if not re.fullmatch(r"G-[A-Z0-9]+", mid):
        return {"ok": False, "error": f"invalid measurement_id: {mid!r}"}

    data = _load_registry()
    projects: List[Dict[str, Any]] = data.setdefault("projects", [])
    target = None
    for p in projects:
        if p.get("slug") == slug.strip():
            target = p
            break
    if not target:
        return {"ok": False, "error": f"slug not found: {slug}"}

    analytics = target.setdefault("analytics", {})
    analytics["ga4"] = {
        "measurement_id": mid,
        "property_id": str(property_id).strip(),
        "website_url": website_url.strip(),
        "stream_name": stream_name.strip(),
        "synced_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    try:
        _save_registry(data)
    except (PermissionError, OSError) as exc:
        return {"ok": False, "error": str(exc)}

    return {"ok": True, "launcher": st, "slug": slug, "analytics_ga4": analytics["ga4"]}


def keymaster_status() -> Dict[str, Any]:
    """Detect whether local Keymaster bootstrap files are expected in resolved projects."""
    db_path = _env_path("GA4_KEYMASTER_DATABASE", "KEYMASTER_DATABASE_PATH")
    vault_path = _env_path("GA4_KEYMASTER_VAULT", "KEYMASTER_VAULT_PATH")
    hints: List[str] = []
    if db_path and db_path.is_file():
        hints.append("keymaster_database_file_present")
    if vault_path and vault_path.is_dir():
        hints.append("keymaster_vault_dir_present")
    available = bool(hints) or os.environ.get("GA4_KEYMASTER_HINTS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    return {
        "available": available,
        "database_path": str(db_path) if db_path else None,
        "vault_path": str(vault_path) if vault_path else None,
        "hints": hints,
        "reason": (
            None
            if available
            else "Optional: set GA4_KEYMASTER_DATABASE / KEYMASTER_DATABASE_PATH or GA4_KEYMASTER_HINTS=true. "
            "Per-repo .keymaster/ is detected via resolve_project_for_ga4."
        ),
    }


def keymaster_bootstrap_at(project_dir: str | Path) -> Dict[str, Any]:
    root = Path(project_dir).expanduser().resolve()
    key_file = root / KEYMASTER_DIR / BOOTSTRAP_KEY_FILE
    if not key_file.is_file():
        return {"available": False, "path": str(key_file), "reason": "no .keymaster/project.key"}
    try:
        data = json.loads(key_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"available": False, "path": str(key_file), "error": str(exc)}
    return {
        "available": True,
        "path": str(key_file),
        "project_slug": data.get("project_slug"),
        "message": "Use keymaster MCP in the agent session for secret storage; GA4 measurement ids stay in .ga4.config.json.",
    }


def build_agent_integration_hints(ctx: Dict[str, Any]) -> List[str]:
    hints: List[str] = []
    launcher = ctx.get("launcher") or {}
    if launcher.get("available"):
        hints.append("launcher_registry: use list_registry_projects_for_ga4 or registry slug in provision flow")
    else:
        hints.append("launcher_registry: unset — pass explicit project_dir and website_url")

    km = ctx.get("keymaster") or {}
    if km.get("available"):
        slug = km.get("project_slug") or "?"
        hints.append(
            f"keymaster: project_slug={slug} — register GA service account via keymaster_register_key "
            "(service e.g. google_analytics_admin); do not store measurement_id as a secret"
        )
    elif keymaster_status().get("available"):
        hints.append("keymaster: host vault present — compose keymaster MCP for credential ingestion")
    else:
        hints.append("keymaster: not detected — use GOOGLE_APPLICATION_CREDENTIALS on the MCP host")

    if ctx.get("suggested_web_roots"):
        hints.append(
            "nextjs: try scaffold_ga4_nextjs_tracking with suggested_web_roots[0] after provisioning"
        )
    return hints


def integration_status() -> Dict[str, Any]:
    return {
        "ok": True,
        "launcher": launcher_status(),
        "keymaster": keymaster_status(),
        "env_docs": {
            "GA4_LAUNCHER_REGISTRY_JSON": "Path to launcher registry.json (read)",
            "GA4_LAUNCHER_REGISTRY_WRITABLE": "true to allow sync_ga4_to_launcher_registry",
            "GA4_KEYMASTER_DATABASE": "Optional path to keymaster.db for status only",
            "GA4_KEYMASTER_HINTS": "true to emit keymaster composition hints without db path",
        },
    }
