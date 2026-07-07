# ai-google-analytics-mcp

MCP server to **provision** Google Analytics 4 for local AI/web projects: create properties and web data streams, capture measurement IDs, inject `gtag` into HTML, and write `.ga4.config.json` in project roots.

For **reporting and monitoring**, use Google's official read-only [`analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp) alongside this server (see `CONTEXT.md`).

## Tools

| Tool | Purpose |
|------|---------|
| `get_ga4_auth_setup_instructions` | gcloud ADC + API enablement steps |
| `list_ga_account_summaries` | Discover accounts/properties (readonly Admin API) |
| `provision_ga4_property` | Create GA4 property under an account |
| `create_web_data_stream` | Create web stream → `G-XXXXXXXX` |
| `render_ga4_gtag_snippet` | HTML snippet for a measurement ID |
| `inject_ga4_gtag_into_file` | Patch a local HTML/layout file |
| `render_ga4_nextjs_component` | Next.js `GoogleAnalytics.tsx` source (env or inline id) |
| `scaffold_ga4_nextjs_tracking` | Write component, wire `layout.tsx`, set `.env.local` |
| `save_project_ga4_config` | Write `.ga4.config.json` in a project dir |
| `provision_project_ga4_setup` | Property + stream + optional config/inject (+ optional `registry_slug`) |
| `get_ga4_integration_status` | Whether launcher/keymaster hooks are configured |
| `list_registry_projects_for_ga4` | Registry projects + `.ga4.config.json` / `.keymaster` hints |
| `resolve_project_for_ga4` | Slug and/or path → website_url, web roots, agent hints |
| `sync_ga4_to_launcher_registry` | Write `analytics.ga4` on registry row (opt-in write) |

### Optional: launcher registry & keymaster

Public-repo safe: **no hardcoded paths**, no imports from sibling repos. Set env on your MCP host only if you use these services:

- `GA4_LAUNCHER_REGISTRY_JSON` — read launcher `registry.json` (same format as launcher-project-registry)
- `GA4_LAUNCHER_REGISTRY_WRITABLE=true` — allow `sync_ga4_to_launcher_registry` / `registry_slug` on provision
- `GA4_KEYMASTER_DATABASE` or `GA4_KEYMASTER_HINTS=true` — status hints only; **secrets stay in keymaster MCP** (`keymaster_register_key` for GA service accounts). Measurement IDs remain in `.ga4.config.json`.

See `docs/adr/0003-optional-registry-keymaster-hooks.md`.

## Quick start

```bash
cd /path/to/ai-google-analytics-mcp
uv sync
uv run pytest -q
uv run ga4-provision-mcp
```

### Authentication

**Full walkthrough:** [Google Analytics GA4 Service Account Setup Guide](google-analytics-ga4-service-account-setup-guide.md) — GCP project, enable Admin (and optional Data) API, create a service account, grant GA account access, and point `GOOGLE_APPLICATION_CREDENTIALS` at the JSON key.

If `gcloud auth application-default login` shows **"This app is blocked"**, use a **service account** (recommended): see also `research/notes/gcloud-this-app-is-blocked.md`.

```bash
# After SA JSON is on disk and SA email has Editor on your GA account:
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/ga4/ga4-provisioner-sa.json
```

Copy `.env.example` → `.env` and set `GOOGLE_APPLICATION_CREDENTIALS` + optional `GA4_DEFAULT_ACCOUNT_ID`.

## Hermes / MCP config (stdio)

```yaml
# ~/.hermes/config.yaml (example)
mcp_servers:
  ga4_provision:
    command: uv
    args:
      - run
      - --directory
      - /path/to/ai-google-analytics-mcp
      - ga4-provision-mcp
```

Companion (read-only reports):

```yaml
  google_analytics:
    command: pipx
    args: ["run", "analytics-mcp"]
    env:
      CLOUDSDK_CORE_PROJECT: your-gcp-project-id
```

## Agent workflow example

> "Provision GA4 for this repo: production URL https://my-app.example, inject into `public/index.html`, save config in project root."

The agent calls `provision_project_ga4_setup` with `project_dir` and `inject_html_path`.

## Docs

- [google-analytics-ga4-service-account-setup-guide.md](google-analytics-ga4-service-account-setup-guide.md) — step-by-step Google Cloud + GA4 + service account setup
- `CONTEXT.md` — rules and architecture
- `HERMES.md` — agent smoke + guardrails
- `docs/adr/` — durable decisions
- `research/` — external references (official analytics-mcp, etc.)
- `BRIEF.md` — original Gemini conversation blueprint