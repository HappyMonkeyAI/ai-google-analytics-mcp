#!/usr/bin/env python3
"""GA4 provisioning MCP — spin up properties/streams and wire tracking into repos."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from ga4_provision_mcp import admin as ga_admin
from ga4_provision_mcp import integrations as ga_integrations
from ga4_provision_mcp import nextjs as ga_nextjs
from ga4_provision_mcp.snippets import inject_gtag_into_html, render_gtag_snippet

mcp = FastMCP(
    "ga4-provision-mcp",
    instructions=(
        "Provision GA4 properties and web data streams for local AI/web projects, "
        "then inject gtag snippets or save .ga4.config.json in project roots. "
        "Use list_ga_account_summaries to discover account/property ids. "
        "For traffic reports and realtime metrics, use the separate read-only "
        "official analytics-mcp server (analytics.readonly), not this server."
    ),
)


@mcp.tool()
def get_ga4_auth_setup_instructions() -> Dict[str, str]:
    """Return GCP/GA auth steps. Prefer service account if gcloud ADC shows 'This app is blocked'."""
    return {
        "gcp_apis": "Enable Google Analytics Admin API and Google Analytics Data API.",
        "recommended": (
            "Service account: create key JSON, set GOOGLE_APPLICATION_CREDENTIALS, "
            "add SA email in GA Admin → Account access management as Editor."
        ),
        "adc_login_user": (
            "gcloud auth application-default login "
            "--scopes https://www.googleapis.com/auth/analytics.edit,"
            "https://www.googleapis.com/auth/analytics.readonly,"
            "https://www.googleapis.com/auth/cloud-platform "
            "(Workspace may block — see research/notes/gcloud-this-app-is-blocked.md)"
        ),
        "workspace_unblock": (
            "Admin console → API controls → trust Google Auth Library OAuth client, "
            "or use service account instead."
        ),
        "companion_server": (
            "Install official read-only analytics-mcp (pipx run analytics-mcp) for run_report / monitoring."
        ),
        "env": "GOOGLE_APPLICATION_CREDENTIALS and optional GA4_DEFAULT_ACCOUNT_ID in .env",
    }


@mcp.tool()
def list_ga_account_summaries(limit: int = 20) -> Dict[str, Any]:
    """List GA account summaries and child properties (read-only Admin API)."""
    try:
        summaries = ga_admin.list_account_summaries(limit=min(limit, 50))
        return {"ok": True, "count": len(summaries), "summaries": summaries}
    except ga_admin.AdminApiError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def provision_ga4_property(
    account_id: str,
    project_name: str,
    timezone: str = "Europe/London",
    currency_code: str = "GBP",
    environment: str = "Production",
) -> Dict[str, Any]:
    """
    Create a new GA4 property for a project under a GA account.
    account_id: numeric id only (e.g. 12345678) or accounts/12345678.
    """
    if not account_id.strip():
        fallback = ga_admin.default_account_id()
        if not fallback:
            return {
                "ok": False,
                "error": "account_id required (or set GA4_DEFAULT_ACCOUNT_ID)",
            }
        account_id = fallback
    try:
        result = ga_admin.provision_property(
            account_id,
            project_name,
            timezone=timezone or os.environ.get("GA4_DEFAULT_TIMEZONE", "Europe/London"),
            currency_code=currency_code or os.environ.get("GA4_DEFAULT_CURRENCY", "GBP"),
            environment=environment,
        )
        return {"ok": True, **result}
    except (ga_admin.AdminApiError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def create_web_data_stream(
    property_id: str,
    stream_name: str,
    website_url: str,
) -> Dict[str, Any]:
    """
    Create a web data stream for a GA4 property. Returns measurement_id (G-XXXXXXXX).
    property_id: numeric or properties/<id>.
    """
    try:
        result = ga_admin.create_web_stream(property_id, stream_name, website_url)
        return {"ok": True, **result}
    except (ga_admin.AdminApiError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def render_ga4_gtag_snippet(measurement_id: str) -> Dict[str, Any]:
    """Return HTML gtag snippet for a measurement ID."""
    try:
        snippet = render_gtag_snippet(measurement_id)
        return {"ok": True, "measurement_id": measurement_id.strip(), "snippet": snippet}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def inject_ga4_gtag_into_file(
    file_path: str,
    measurement_id: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Inject or update GA4 gtag in a local HTML/layout file (absolute path recommended).
    Set dry_run=true to preview without writing.
    """
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        return {"ok": False, "error": f"File not found: {path}"}
    try:
        original = path.read_text(encoding="utf-8", errors="replace")
        updated, action = inject_gtag_into_html(original, measurement_id)
        if dry_run:
            return {
                "ok": True,
                "path": str(path),
                "action": action,
                "would_write": updated != original,
                "preview_bytes": len(updated),
            }
        if updated != original:
            path.write_text(updated, encoding="utf-8")
        return {"ok": True, "path": str(path), "action": action, "written": updated != original}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def render_ga4_nextjs_component(
    measurement_id: str,
    mode: str = "env",
    consent_gated: bool = False,
) -> Dict[str, Any]:
    """
    Return a Next.js client component (next/script) for GA4.
    mode: env (read NEXT_PUBLIC_GA_MEASUREMENT_ID) or inline (embed id).
    consent_gated: only load gtag after localStorage cookie consent is accepted.
    """
    if mode not in ("env", "inline"):
        return {"ok": False, "error": "mode must be 'env' or 'inline'"}
    try:
        source = ga_nextjs.render_nextjs_ga4_component(
            measurement_id,
            mode=mode,  # type: ignore[arg-type]
            consent_gated=consent_gated,
        )
        return {
            "ok": True,
            "measurement_id": measurement_id.strip(),
            "mode": mode,
            "consent_gated": consent_gated,
            "suggested_path": "src/components/GoogleAnalytics.tsx",
            "env_line": ga_nextjs.render_nextjs_env_line(measurement_id),
            "source": source,
        }
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def scaffold_ga4_nextjs_tracking(
    web_root: str,
    measurement_id: str,
    layout_relative: str = "src/app/layout.tsx",
    mode: str = "env",
    consent_gated: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Scaffold GA4 for a Next.js app: write GoogleAnalytics.tsx, wire layout.tsx,
    and set NEXT_PUBLIC_GA_MEASUREMENT_ID in .env.local (when mode=env).
    web_root must be the Next.js package root (directory containing package.json).
    """
    if mode not in ("env", "inline"):
        return {"ok": False, "error": "mode must be 'env' or 'inline'"}
    try:
        result = ga_nextjs.scaffold_nextjs_ga4(
            web_root,
            measurement_id,
            layout_relative=layout_relative,
            mode=mode,  # type: ignore[arg-type]
            consent_gated=consent_gated,
            dry_run=dry_run,
        )
        return {"ok": True, **result}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
def save_project_ga4_config(
    project_dir: str,
    measurement_id: str,
    property_id: str,
    website_url: str,
    stream_name: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Write .ga4.config.json in a project root for agents and humans to reference later."""
    root = Path(project_dir).expanduser().resolve()
    if not root.is_dir():
        return {"ok": False, "error": f"Not a directory: {root}"}
    payload: Dict[str, Any] = {
        "measurement_id": measurement_id.strip(),
        "property_id": ga_admin.normalize_property_id(property_id),
        "website_url": website_url.strip(),
        "stream_name": stream_name.strip(),
    }
    if extra:
        payload["extra"] = extra
    out = root / ".ga4.config.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(out), "config": payload}


@mcp.tool()
def provision_project_ga4_setup(
    account_id: str,
    project_name: str,
    website_url: str,
    project_dir: str = "",
    timezone: str = "Europe/London",
    inject_html_path: str = "",
    registry_slug: str = "",
) -> Dict[str, Any]:
    """
    End-to-end: create property + web stream, optionally save .ga4.config.json and inject gtag.
    If registry_slug is set and GA4_LAUNCHER_REGISTRY_* env is configured, syncs analytics.ga4 metadata.
    """
    prop = provision_ga4_property(account_id, project_name, timezone=timezone)
    if not prop.get("ok"):
        return prop
    stream_name = f"{project_name} Web"
    stream = create_web_data_stream(
        prop["property_id"],
        stream_name,
        website_url,
    )
    if not stream.get("ok"):
        return {"ok": False, "property": prop, "stream_error": stream}
    measurement_id = stream.get("measurement_id", "")
    result: Dict[str, Any] = {
        "ok": True,
        "property": prop,
        "stream": stream,
        "measurement_id": measurement_id,
    }
    if project_dir.strip():
        saved = save_project_ga4_config(
            project_dir,
            measurement_id,
            prop["property_id"],
            website_url,
            stream_name=stream_name,
        )
        result["config_file"] = saved
    if inject_html_path.strip() and measurement_id:
        result["injection"] = inject_ga4_gtag_into_file(inject_html_path, measurement_id)
    if registry_slug.strip() and measurement_id:
        result["registry_sync"] = ga_integrations.sync_ga4_to_launcher_registry(
            registry_slug.strip(),
            measurement_id,
            prop["property_id"],
            website_url=website_url,
            stream_name=stream_name,
        )
    return result


@mcp.tool()
def get_ga4_integration_status() -> Dict[str, Any]:
    """Report optional launcher registry and keymaster hook availability (graceful when unset)."""
    return ga_integrations.integration_status()


@mcp.tool()
def list_registry_projects_for_ga4(filter_query: str = "", limit: int = 50) -> Dict[str, Any]:
    """List launcher registry projects with .ga4.config.json and .keymaster hints when registry env is set."""
    return ga_integrations.list_launcher_projects(filter_query=filter_query, limit=limit)


@mcp.tool()
def resolve_project_for_ga4(slug: str = "", project_dir: str = "") -> Dict[str, Any]:
    """Resolve registry slug and/or filesystem path for GA4 provisioning (paths, website_url, agent hints)."""
    return ga_integrations.resolve_project_for_ga4(slug=slug, project_dir=project_dir)


@mcp.tool()
def sync_ga4_to_launcher_registry(
    slug: str,
    measurement_id: str,
    property_id: str,
    website_url: str = "",
    stream_name: str = "",
) -> Dict[str, Any]:
    """Write GA4 metadata to launcher registry project.analytics.ga4 (requires writable env)."""
    return ga_integrations.sync_ga4_to_launcher_registry(
        slug,
        measurement_id,
        property_id,
        website_url=website_url,
        stream_name=stream_name,
    )


@mcp.resource("ga4://workflow")
def workflow_resource() -> str:
    return (
        "# GA4 dual-server workflow\n\n"
        "1. Provision (this server): property + web stream + gtag injection.\n"
        "2. Monitor (analytics-mcp): run_report, realtime, configuration reads.\n"
        "3. Keep measurement ids in each repo `.ga4.config.json`.\n"
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()