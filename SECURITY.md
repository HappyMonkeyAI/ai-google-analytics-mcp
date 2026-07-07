# Security

This document describes how **ai-google-analytics-mcp** (`ga4-provision-mcp`) handles trust, credentials, and exposure. It is written for operators sharing or deploying the server in public or team environments.

## Transport and network exposure

- The server runs as a **stdio MCP** process only: `mcp.run(transport="stdio")` in `src/ga4_provision_mcp/server.py`.
- It does **not** open an HTTP, SSE, or WebSocket listener. There is no bind address or port in this package.
- Network access is limited to **outbound** calls to **Google Analytics Admin API** (and whatever your host DNS/TLS stack allows). Inbound attack surface from this MCP itself is **not** applicable; risk is bound to the **host OS user** that runs the MCP child process.

## Trust model

Treat this MCP like **shell access plus GA admin** for the credentials you configure:

| Capability | Tool examples | Risk if misused |
|------------|---------------|-----------------|
| GA4 admin (create) | `provision_ga4_property`, `provision_project_ga4_setup` | New properties/streams under the linked GA account |
| Local file write | `inject_ga4_gtag_into_file`, `scaffold_ga4_nextjs_tracking`, `save_project_ga4_config` | Overwrite or modify files at paths the process can write |
| GA discovery (read) | `list_ga_account_summaries` | Enumerate accounts/properties visible to the credential |
| Optional registry write | `sync_ga4_to_launcher_registry` | Mutate one JSON file when `GA4_LAUNCHER_REGISTRY_WRITABLE=true` |

**Any client** that can invoke MCP tools (IDE, Hermes, Claude Desktop, etc.) can trigger these actions. Prompt injection in the **orchestrating agent** is in scope: do not run this MCP against repos or chats you do not trust unless you supervise tool use.

There is **no** path sandbox: `file_path` and `web_root` are resolved on the host filesystem.

## Credentials and secrets

- **Never commit** service account JSON, `.env`, or OAuth client secrets. `.gitignore` excludes common patterns; verify before `git push`.
- Configure auth only via host environment, typically:
  - `GOOGLE_APPLICATION_CREDENTIALS` → path to a service account key file
  - Optional: `GA4_DEFAULT_ACCOUNT_ID`, `CLOUDSDK_CORE_PROJECT`
- Follow [google-analytics-ga4-service-account-setup-guide.md](google-analytics-ga4-service-account-setup-guide.md) for GCP/GA setup.
- **Measurement IDs** (`G-XXXXXXXX`) are public in HTML; they are not vault secrets. **Service account keys** are secrets.

### Recommended credential separation

| Role | Suggested GA / GCP access |
|------|---------------------------|
| **This server (provision)** | Service account with **Editor** on the specific GA **account** (or property) you use for provisioning — not org-wide Owner unless intentional |
| **Reporting** | Separate service account with **Viewer** / readonly + official [`analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp) |

Revoke or rotate keys if a host is compromised or a key file is exposed.

## Optional integrations (off by default)

These are **opt-in** via environment variables only; the public package does not hardcode paths to private infrastructure.

| Variable | Effect |
|----------|--------|
| `GA4_LAUNCHER_REGISTRY_JSON` | Read a launcher-style `registry.json` (project paths, URLs) |
| `GA4_LAUNCHER_REGISTRY_WRITABLE=true` | Allow writing `analytics.ga4` metadata into that file |
| `GA4_KEYMASTER_DATABASE` / `GA4_KEYMASTER_HINTS` | Status hints only; **this server does not read vault secrets** |

Leave registry writes disabled unless you intend agents to update that file.

## Dependencies

Runtime dependencies are declared in `pyproject.toml` (`mcp`, `google-analytics-admin`). Keep `uv lock` / installs current and review upstream advisories for those packages.

## Safe usage checklist

1. Run MCP **locally** or on a machine you control; stdio parent must be trusted.
2. Use a **dedicated** provisioning service account with minimum GA access needed.
3. Use `dry_run=true` on inject/scaffold when exploring unfamiliar layouts.
4. Do not enable `GA4_LAUNCHER_REGISTRY_WRITABLE` on shared or production registry files without review.
5. Pair with **read-only** `analytics-mcp` for reporting; do not grant `analytics.edit` to reporting-only workflows.
6. Review agent transcripts if tools modified unexpected paths or created unexpected GA properties.

## Vulnerability reporting

If you believe you have found a security issue in **this repository** (not in Google Cloud or GA itself), please report it privately to the maintainer listed in `pyproject.toml` authors rather than opening a public issue with exploit details. Include steps to reproduce and impact (stdio trust boundary, file paths, credential handling).

We do not operate a bug bounty program for this open-source project.

## Out of scope

- Security of Google Analytics, Google Cloud IAM, or third-party MCP hosts (Hermes, Cursor, etc.)
- Content injected into user websites beyond standard Google `gtag.js` (operators are responsible for privacy/cookie compliance on their sites)