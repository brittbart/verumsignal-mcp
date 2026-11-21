# Verum Signal MCP Server

<!-- mcp-name: io.github.brittbart/verumsignal-mcp -->

An MCP server that gives LLM agents Verum Signal's rated political claims: what candidates and leaders said at debates and press conferences, who said each one, and how each was rated, plus the claims news outlets report. One search covers both, and a live view shows what is being rated right now. Requires a Verum Signal API key.

## What the tools do

| Tool | Returns | Explicitly does NOT |
|---|---|---|
| `search_claims` | Start here for a topic question. Rated claims about a topic from live events (debates and press conferences) and from news outlets in one call, newest first, each with its rating, who said it, and a link to its page. Narrow by event type, rating and date. | Store what you searched for: search terms travel in the request and are not kept. |
| `list_event_claims` | Rated claims from every public debate and press conference, filtered by topic, event type, rating and date, with a cursor for the next page. | Score anyone: no counts or totals by rating are returned. |
| `live_now` | Whether a debate or press conference is being covered live, with its page and its newest rated claims; otherwise the next listed event. | Show ratings as final while they are provisional: each claim says which it is. |
| `list_debates` | Available debates with claim counts, dates, and status. | Include the claims themselves — call `get_debate_verdicts` for that. |
| `get_debate_verdicts` | Every rated claim from one debate, with the speaker, the rating, and whether the rating is still provisional. Paginates automatically to completeness. | Truncate silently. If a debate is large enough to hit an internal safety cap, the response includes an explicit `truncated: true` flag rather than quietly returning a partial result. |
| `list_recent_claims` | Claims reported by news outlets, with their ratings. Pass `q` to find claims about a topic; filter by outlet or rating; without `q`, most recent first. | Return quoted claims an outlet attributes to someone else, or any overall score for an outlet. |
| `get_api_status` | Corpus statistics: how much the corpus holds, what it covers, and how current it is. | Include per-claim detail — call the other tools for that. |

Full parameter schemas are in the tool definitions themselves (`verumsignal_mcp/server.py`), and are also what any MCP client will show you directly. This table is a summary; the tool definitions are authoritative.

## Install & config

Requires Python 3.9+ and no third-party dependencies.

**Claude Desktop, one click:** download `verumsignal-mcp-0.3.0.mcpb` from the [latest release](https://github.com/brittbart/verumsignal-mcp/releases/latest) and open it. Claude Desktop installs the server and asks for your API key.

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

The PyPI package is at 0.2.0 for now, without `search_claims`, `list_event_claims` and `live_now`. To run 0.3.0 with uv before it catches up, use `"args": ["--from", "git+https://github.com/brittbart/verumsignal-mcp", "verumsignal-mcp"]`.

**With pip:**

```bash
pip install verumsignal-mcp
```

then use `"command": "verumsignal-mcp"` with no `args` in the config above.

**From a clone:** `git clone https://github.com/brittbart/verumsignal-mcp.git` and use `"command": "python3"`, `"args": ["/absolute/path/to/mcp_server.py"]`.

These examples are for Claude Desktop's `claude_desktop_config.json`; other MCP clients take the same command, arguments and environment.

**Verify it works:** ask your agent "what has been claimed about tariffs, according to Verum Signal?" A correctly wired server returns rated claims from debates, press conferences and the news, each with a link. If you see an authentication error, check the key; if you see a connection error, confirm outbound HTTPS access to `api.verumsignal.com` is allowed from wherever the server runs.

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

This server is at **v0.3.0**, an honest pre-1.0 number. It targets API version v1. Ratings carry the methodology version they were made under. See `CHANGELOG.md` for version history.

## Known limitations

- **Outlet-level scores are not served.** The tools return individual claims and their ratings only.
- **No rating reasoning.** A deliberate boundary — see "The data boundary" above.
- **Live ratings can be provisional.** Each debate and press-conference claim says whether its rating is still provisional; ratings become final after the post-event review.
- **Search is a substring match.** A phrase matches only claims that contain it; when nothing matches, the response says how many claims contain each word.
- **Data freshness:** the API's cache refreshes every 5 minutes. This server's data is exactly as fresh as that cache.
