# Verum Signal MCP Server

An MCP server exposing Verum Signal's public API to LLM agents. Self-hosted. Requires a Verum Signal API key.

## What the tools do

| Tool | Returns | Explicitly does NOT |
|---|---|---|
| `get_outlet_score` | An outlet's credibility score (0-100), tier, and verdict-count breakdown. | Return the reasoning behind any verdict. |
| `list_recent_claims` | Recent claims, optionally filtered by outlet, verdict, or claim origin, in recency order. | **Perform text search. It is not a search tool.** It was renamed from `search_claims` precisely because it never searched. |
| `get_debate_verdicts` | All claims from a political debate, with speaker attribution and verdicts. Paginates automatically to completeness. | Truncate silently. If a debate is large enough to hit an internal safety cap, the response includes an explicit `truncated: true` flag rather than quietly returning a partial result. |
| `list_debates` | Available debates with claim counts, dates, and status. | Include the actual claims or verdicts from each debate — call `get_debate_verdicts` for that. |
| `get_api_status` | Corpus-level statistics: total claims, total outlets tracked, methodology version in effect, last refresh time. | Include per-outlet or per-claim detail — call `get_outlet_score` or `list_recent_claims` for that. |

Full parameter schemas are in the tool definitions themselves (`mcp_server.py`), and are also what any MCP client will show you directly — this table is a summary, not the source of truth.

## The data boundary

FAQ 06 promises verdict reasoning is not available through the API, and that promise is kept structurally: the underlying `SELECT` statements never fetch `verdict_summary`, `evidence_sources`, `priority_score`, or `verification_attempts`, and the sync layer that populates the API's cache never populates those fields either. It isn't a filter applied after the fact — the data simply isn't in what this server can reach.

What this server sends out: an authenticated `GET` request to `api.verumsignal.com` (or an operator-configured `VS_API_BASE`) for each tool call.

What it sends back to the calling agent: whatever that API call returns — scores, verdicts, claims, debate data, corpus statistics.

What it never touches: this server makes no network connections to anything other than the configured API host, reads and writes no local files, and includes no telemetry or analytics of any kind. Its entire dependency footprint is three lines of Python standard library (`json`, `os`, `sys`, `urllib`) — nothing else is imported, and nothing else runs.

## Key handling

`VS_API_KEY` is read from the environment (`os.environ.get("VS_API_KEY", "")`) and is never hardcoded. The server has no logging of any kind — no log calls exist anywhere in it — and both of its exception-handling paths only stringify the exception object itself, never any variable that could contain the key. There is no code path by which the key can reach output, a log, or a file.

You can provide the key two ways:

1. **In the MCP client's config file**, as shown below. Once you do this, that config file contains a live credential and should be protected the same way you'd protect any other secret file (restricted permissions, not committed to version control, etc.).
2. **As an ambient environment variable**, set by your shell, your OS's secrets manager, or however your team manages credentials — since the server reads from the environment regardless of where that environment variable was set. If your security team has a preference here, this is almost always it.

**Key rotation is manual.** There is no self-service key issuance or rotation endpoint today. To get or rotate a key, contact Verum Signal directly.

## Install & config

Requires Python 3.9+ and no third-party dependencies.

1. Clone this repo:
```bash
   git clone https://github.com/brittbart/verumsignal-mcp.git
```
2. No dependency install step is needed — the server uses only the Python standard library.
3. Add this to your MCP client's config (this example is for Claude Desktop's `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "verum-signal": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": { "VS_API_KEY": "vs_live_..." }
    }
  }
}
```

**Verify it works:** ask your agent for an outlet's credibility score — for example, "what's the credibility score for nytimes.com?" A correctly-wired server returns a real number between 0 and 100, a tier, and a breakdown of verdict counts. If instead you see an authentication error, double check the key; if you see a connection error, confirm outbound HTTPS access to `api.verumsignal.com` is permitted from wherever the server runs.

## Rate limits & quota

Your API key's tier governs what you get:

| Tier | Requests/minute | Calls/month |
|---|---|---|
| Starter | 60 | 5,000 |
| Pro | 180 | 50,000 |
| Enterprise | Custom | Custom |

Every tool response includes a `_quota` field showing your remaining budget on both dimensions (e.g. `rate_limit_remaining`, `monthly_quota_remaining`) — an agent can check this before deciding whether to make another call, rather than finding out by hitting a 429.

**One honest note on the rate limiter's behavior:** it enforces a fixed one-minute wall-clock window, not a true sliding window. In practice this means a burst of requests spanning a minute boundary could very briefly exceed the nominal per-minute rate — the same tradeoff GitHub's and Stripe's own rate limiters make, in exchange for the limiter being atomic and not serializing requests against each other. It's bounded and it isn't a defect, but if you're measuring the limiter precisely, you should hear this from us first.

## Versioning

This server is at **v0.1.0** — an honest version number for a closed-beta artifact, not inflated to suggest more maturity than it has. It targets API version v1, and the methodology version currently in effect is **v1.6**. See `CHANGELOG.md` for version history.

## Known limitations

Stated plainly, because you'll find these anyway and it's better to hear them from us first:

- **No text search.** `list_recent_claims` filters by outlet, verdict, and claim origin — it does not search claim text or topics. Server-side search is a known gap.
- **No verdict reasoning.** This is a deliberate boundary, not a missing feature — see "The data boundary" above.
- **Key rotation is manual.** No self-service issuance or rotation exists yet.
- **Data freshness:** the underlying API's cache refreshes every 5 minutes. This server's data is exactly as fresh as that cache — no fresher, no staler.
