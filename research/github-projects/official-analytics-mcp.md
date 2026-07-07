# official analytics-mcp (Google)

- **URL:** https://github.com/googleanalytics/google-analytics-mcp
- **License:** Apache-2.0 (verify on repo)
- **Stack:** Python MCP, GA Data API (read-only)
- **Why it matters:** Companion server for `run_report` / monitoring after this repo provisions streams.
- **Cherry-pick:** pipx invocation, env `CLOUDSDK_CORE_PROJECT`, tool names for reports.
- **Avoid:** Expecting it to create properties — use `ai-google-analytics-mcp` instead.