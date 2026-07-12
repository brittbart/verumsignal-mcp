# Changelog

All notable changes to the Verum Signal MCP server are documented here.

## [0.1.1] — 2026-07-12

### Fixed

- `Retry-After` is now surfaced in the `_quota` field on rate-limit errors. The REST API has always sent this header on 429s caused by the per-minute rate limit; the MCP server's header mapping simply never looked for it, so an agent hitting a rate limit saw `rate_limit_remaining: 0` with no indication of how long to wait before retrying. It now appears as `retry_after_seconds` alongside the other quota fields whenever the API sends it — not present on successful calls or monthly-quota rejections, since a fixed retry time is meaningless for a quota that resets monthly rather than every minute.

## [0.1.0] — 2026-07-12

Initial packaged release.

### Breaking changes

- **`search_claims` renamed to `list_recent_claims`.** The original tool never performed text search — it filtered and returned recent claims, with a "search" name that implied a capability it didn't have. Any integration calling `search_claims` by name will need to update to `list_recent_claims`. The tool's `query` parameter has also been removed entirely, since it was never validated or used server-side; `outlet`, `verdict`, and the newly-added `claim_origin` remain as filters.
- **`get_debate_verdicts` now returns complete results.** Previously, debates with more than 50 claims were silently truncated to the first 50 with no indication anything was missing. It now paginates through the full result set automatically. An integration built against the old truncated behavior will now receive more claims per call than it did before — for most consumers this is strictly an improvement, but it is a change in response size and shape worth knowing about.

### Fixed

- `get_outlet_score`'s `scoreable_claims` field previously always returned `null` due to a field-name mismatch against the underlying API response; it now returns the real value.
- Error responses now include the actual message from the API (e.g. "Outlet not found: example.com") instead of a generic HTTP reason phrase.
- Every tool response now includes a `_quota` field reflecting the calling key's current rate-limit and monthly-quota status.

### Removed

- Dead code in two tool handlers that referenced a `verdict_summary` field the API never returns. This was inert (always `null`), not a live leak, but was removed as a precaution — it's exactly the kind of code that could start leaking real data the day someone else changes an unrelated part of the API without knowing why that field was excluded.
