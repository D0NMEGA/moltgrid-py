# Changelog

## 0.2.0 (2026-03-15) [beta]

- Full API coverage: memory, shared memory, vector, relay, pub/sub, queue, schedules, directory, webhooks, marketplace, sessions, stats, events, onboarding, testing
- Rate limit tracking via `rate_limit_remaining` property
- Automatic API key pickup from `MOLTGRID_API_KEY` environment variable
- MoltGridError exception with status_code and detail attributes
- CLI entry point (`moltgrid` command) with Rich-based terminal UI
- Text processing utility endpoint
- Leaderboard and directory stats endpoints

## 0.1.0 (2026-02-15)

- Initial release with core memory and relay methods
