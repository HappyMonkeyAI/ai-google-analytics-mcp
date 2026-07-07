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
| `save_project_ga4_config` | Write `.ga4.config.json` in a project dir |
| `provision_project_ga4_setup` | Property + stream + optional config/inject |

## Quick start

```bash
cd /path/to/ai-google-analytics-mcp
uv sync
uv run pytest -q
uv run ga4-provision-mcp
```

### Authentication

If `gcloud auth application-default login` shows **"This app is blocked"**, use a **service account** (recommended): see `research/notes/gcloud-this-app-is-blocked.md`.

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

- `CONTEXT.md` — rules and architecture
- `HERMES.md` — agent smoke + guardrails
- `docs/adr/` — durable decisions
- `research/` — external references (official analytics-mcp, etc.)
- `BRIEF.md` — original Gemini conversation blueprint