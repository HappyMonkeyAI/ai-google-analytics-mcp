# CONTEXT — ai-google-analytics-mcp

GA4 **provisioning** MCP for Stephen's local AI and web projects: create properties/streams, wire measurement IDs into repos, keep a machine-readable `.ga4.config.json` per project.

## Source of truth

1. `CONTEXT.md` (this file) — operating rules
2. `docs/adr/` — architecture decisions
3. Code under `src/ga4_provision_mcp/`
4. `research/` — external references only
5. `BRIEF.md` — historical design notes from Gemini (not canonical over ADRs)

## Stack & runtime

- Python ≥ 3.10, **uv**
- FastMCP stdio (`ga4-provision-mcp` entrypoint)
- `google-analytics-admin` (Analytics Admin API, **write** for provision tools)
- Auth: **ADC** — prefer **service account JSON** (`GOOGLE_APPLICATION_CREDENTIALS`) with GA **Editor** on the account; user `gcloud auth application-default login` often hits Workspace **"This app is blocked"** on `analytics.edit` (see `research/notes/gcloud-this-app-is-blocked.md`)

## Architecture (dual server)

| Role | Server | Scope |
|------|--------|--------|
| Provision + repo wiring | **This repo** (`ga4-provision-mcp`) | `analytics.edit` (create property/stream, inject gtag, save config) |
| Reports / monitoring | **Official** `analytics-mcp` (pipx) | `analytics.readonly` — `run_report`, realtime, read config |

Do not implement full reporting here; document and configure the companion server instead.

## Non-negotiable rules

1. **No secrets in git** — ADC on host; optional `.env` for defaults only.
2. **Explicit paths** — file injection tools require resolved paths; prefer absolute project paths.
3. **Dry-run first** on unfamiliar layouts: `inject_ga4_gtag_into_file(..., dry_run=true)`.
4. **One property per deployable** unless Stephen asks for staging streams explicitly.
5. **Verifiable outputs** — return property id, stream name, measurement id, and written file paths.
6. **Default locale** — `Europe/London`, `GBP` unless overridden per project.

## Workflow

1. `get_ga4_auth_setup_instructions` or `list_ga_account_summaries` to pick `account_id`.
2. `provision_ga4_property` + `create_web_data_stream` (or `provision_project_ga4_setup`).
3. `save_project_ga4_config` in repo root; add `.ga4.config.json` to git if not secret (measurement ids are public in HTML).
4. `inject_ga4_gtag_into_file` on `index.html`, layout template, or Next.js `app/layout.tsx` (HTML export) as appropriate.
5. Later: agent uses **analytics-mcp** for traffic questions referencing stored property/measurement ids.

## Optional integrations (launcher / keymaster)

- **Launcher registry**: env `GA4_LAUNCHER_REGISTRY_JSON` → `resolve_project_for_ga4`, `list_registry_projects_for_ga4`. Optional write: `GA4_LAUNCHER_REGISTRY_WRITABLE=true` + `sync_ga4_to_launcher_registry` or `registry_slug` on `provision_project_ga4_setup`.
- **Keymaster**: this server does not call keymaster MCP. It detects `.keymaster/project.key` under resolved paths and returns `project_slug` for agents to compose **keymaster MCP** for credential storage. GA measurement IDs are not vault secrets.
- If env is unset, tools return `available: false` with a reason — core provisioning unchanged.

## Exposure

| Channel | Id |
|---------|-----|
| Launcher registry | slug `ai-google-analytics-mcp` |
| Hermes `mcp_servers` | e.g. `ga4_provision` |
| Dynamic MCP catalogue | `ga4_provision` (when registered) |

## What not to do

- Do not commit service account JSON or OAuth client secrets.
- Do not use this server for bulk destructive Admin API changes without explicit approval.
- Do not replace official analytics-mcp for reporting.
- Do not assume Gemini snippet imports (`mcp.server.fastapi`) — use `mcp.server.fastmcp` like other Stephen MCP repos.

## Paths

| Path | Role |
|------|------|
| `src/ga4_provision_mcp/server.py` | MCP tools |
| `src/ga4_provision_mcp/admin.py` | Admin API |
| `src/ga4_provision_mcp/snippets.py` | gtag HTML |
| `src/ga4_provision_mcp/nextjs.py` | Next.js component + scaffold |
| `src/ga4_provision_mcp/integrations.py` | Optional launcher registry + keymaster hints |
| `scripts/scan_ga4_project_configs.py` | Inventory scan |
| `tests/` | unit tests (mocked Admin API) |
| `docs/adr/` | decisions |