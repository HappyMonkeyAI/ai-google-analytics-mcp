# gcloud "This app is blocked" on ADC login

## What happened

`gcloud auth application-default login --scopes ...analytics.edit...` uses Google's **Google Auth Library** OAuth client. Workspace and some personal accounts show:

> This app is blocked — This app tried to access sensitive info in your Google Account.

That is expected for **Analytics Admin write** scopes when the client is not trusted in your org.

## Fix options (pick one)

### A. Service account (recommended for MCP / Hermes)

Best for a long-running local agent: no browser, no "blocked app" screen.

1. **GCP** (your cloud project): APIs enabled — Analytics Admin API, Analytics Data API.
2. **IAM → Service accounts** → create e.g. `ga4-provisioner@YOUR_PROJECT.iam.gserviceaccount.com` → **Keys** → JSON → save outside git, e.g. `~/.config/ga4/ga4-provisioner-sa.json` (mode 600).
3. **Google Analytics** (analytics.google.com): **Admin** → **Account access management** (and/or property access) → **Add users** → paste the **service account email** → role **Editor** (needed to create properties/streams).
4. On the Hermes host:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/ga4/ga4-provisioner-sa.json
# optional in Hermes mcp_servers env for ga4_provision
```

5. Smoke: `uv run --directory /home/stephen/projects/ai-google-analytics-mcp ga4-provision-mcp` then tool `list_ga_account_summaries`.

Official `analytics-mcp` can use the same SA with **Viewer** on GA if you only need readonly reporting — or a separate SA.

### B. Workspace admin trusts Google Auth Library

If you use **Google Workspace** and want **your user** ADC (not a SA):

1. [Google Admin](https://admin.google.com) → **Security** → **Access and data control** → **API controls** → **Manage third-party app access** → **Configure new app**.
2. Search by **OAuth client ID** (not the name "Google Auth Library" — it often won't appear by name). Community posts reference client id `32555940559.apps.googleusercontent.com` for the gcloud/Google Auth Library flow — verify in your error/details screen if Google shows a different id.
3. Set app to **Trusted** for your org (or allow the user).
4. Retry ADC login with scopes.

Refs: [Akingscote — unverified auth library](https://akingscote.co.uk/posts/gcloud-unconfigured-third-party-apps/), Google support threads on "This app is blocked" during `gcloud auth application-default login`.

### C. Your own OAuth desktop client (advanced)

Create an OAuth **Desktop** client in GCP → use `gcloud auth application-default login --client-id-file=... --scopes=...` per [gcloud ADC docs](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login). More setup; use if SA is not acceptable.

## What not to do

- Do not commit SA JSON or OAuth client secrets into `ai-google-analytics-mcp`.
- Do not assume ADC user login will work on Workspace without admin trust or SA.