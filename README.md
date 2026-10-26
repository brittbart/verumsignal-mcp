# Verum Signal MCP Server

<!-- mcp-name: io.github.brittbart/verumsignal-mcp -->

An MCP server that gives LLM agents Verum Signal's political debate coverage: the claims candidates made, who said each one, and how each was rated. It also searches the claims news outlets report. Requires a Verum Signal API key.

## What the tools do

| Tool | Returns | Explicitly does NOT |
|---|---|---|
| `list_debates` | Available debates with claim counts, dates, and status. | Include the claims themselves — call `get_debate_verdicts` for that. |
| `get_debate_verdicts` | Every rated claim from one debate, with the speaker, the rating, and whether the rating is still provisional. Paginates automatically to completeness. | Truncate silently. If a debate is large enough to hit an internal safety cap, the response includes an explicit `truncated: true` flag rather than quietly returning a partial result. |
| `list_recent_claims` | Claims reported by news outlets, with their ratings. Pass `q` to find claims about a topic; filter by outlet or rating; without `q`, most recent first. | Return quoted claims an outlet attributes to someone else, or any overall score for an outlet. |
| `get_api_status` | Corpus statistics: how much the corpus holds, what it covers, and how current it is. | Include per-claim detail — call the other tools for that. |

Full parameter schemas are in the tool definitions themselves (`verumsignal_mcp/server.py`), and are also what any MCP client will show you directly. This table is a summary; the tool definitions are authoritative.

## Install & config

Requires Python 3.9+ and no third-party dependencies.

**With uv** (nothing to install first):

```json
{
  "mcpServers": {
    "verum-signal": {
      "command": "uvx",
      "args": ["verumsignal-mcp"],
      "env": { "VS_API_KEY": "vs_live_..." }
    }
  }
}
```

**With pip:**

```bash
pip install verumsignal-mcp
```

then use `"command": "verumsignal-mcp"` with no `args` in the config above.

**From a clone:** `git clone https://github.com/brittbart/verumsignal-mcp.git` and use `"command": "python3"`, `"args": ["/absolute/path/to/mcp_server.py"]`.

These examples are for Claude Desktop's `claude_desktop_config.json`; other MCP clients take the same command, arguments and environment.

**Verify it works:** ask your agent "which debates does Verum Signal cover?" A correctly wired server returns a list of debates with dates and claim counts. If you see an authentication error, check the key; if you see a connection error, confirm outbound HTTPS access to `api.verumsignal.com` is allowed from wherever the server runs.

## Getting a key

Keys are issued to Verum Signal account holders. See [verumsignal.com/developers](https://verumsignal.com/developers).

## The data boundary

Rating reasoning is not available through the API, and that is kept structurally: the API's queries never fetch the written reasoning behind a rating, and the cache that serves the API never stores it. It isn't a filter applied after the fact — the data simply isn't in what this server can reach.

What this server sends out: an authenticated `GET` request to `api.verumsignal.com` (or an operator-configured `VS_API_BASE`) for each tool call.

What it sends back to the calling agent: whatever that API call returns.

What it never touches: this server makes no network connections to anything other than the configured API host, reads and writes no local files, and includes no telemetry or analytics of any kind. It uses only the Python standard library (`json`, `os`, `sys`, `urllib`).

## Key handling

`VS_API_KEY` is read from the environment and is never hardcoded. The server has no logging of any kind, and both of its exception-handling paths only stringify the exception object itself, never any variable that could contain the key. There is no code path by which the key can reach output, a log, or a file.

You can provide the key two ways:

1. **In the MCP client's config file**, as shown above. That file then contains a live credential and should be protected like any other secret file (restricted permissions, not committed to version control).
2. **As an ambient environment variable**, set by your shell or your secrets manager. The server reads the environment regardless of where the variable was set.

## Rate limits & quota

Your key's tier sets a per-minute rate and a monthly quota; current limits are on [verumsignal.com/developers](https://verumsignal.com/developers). Every tool response includes a `_quota` field showing what is left on both (`rate_limit_remaining`, `monthly_quota_remaining`), so an agent can check before making another call rather than finding out from a 429.

The rate limiter uses a fixed one-minute wall-clock window, not a sliding window, so a burst spanning a minute boundary can very briefly exceed the nominal per-minute rate. It's bounded, and you should hear it from us first.

## Versioning

This server is at **v0.2.0**, an honest pre-1.0 number. It targets API version v1. Ratings carry the methodology version they were made under. See `CHANGELOG.md` for version history.

## Known limitations

- **Outlet-level scores are not served.** The tools return individual claims and their ratings only.
- **No rating reasoning.** A deliberate boundary — see "The data boundary" above.
- **Debate ratings can be provisional.** Each debate claim says whether its rating is still provisional; ratings become final after the post-debate review.
- **Data freshness:** the API's cache refreshes every 5 minutes. This server's data is exactly as fresh as that cache.
