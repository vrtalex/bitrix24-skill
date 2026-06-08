# Changelog

All notable changes to the `bitrix24-agent` skill. Versions follow semantic versioning,
declared in `skills/bitrix24-agent/SKILL.md` frontmatter (`metadata.version`). Method metadata
is generated from the official universal documentation
([apidocs.bitrix24.com](https://apidocs.bitrix24.com) / [bitrix24/b24restdocs](https://github.com/bitrix24/b24restdocs)).

## [2.0.0] — 2026-06-08

### Skill
- Universal CRM via `crm.item.*` as the primary path; ~270 curated methods across 16 capability
  packs (core, comms, automation, collaboration, content, boards, commerce, services, platform,
  sites, compliance, diagnostics, bots, booking, mail, templates).
- Per-pack method catalogs with Risk / Scope / Required / Deprecated / Docs columns, plus
  workflow chains for common scenarios: lead intake, de-duplication, activity logging,
  deal-stage resolution, products with tax/discount, order-to-payment, task-with-file,
  bulk export, and offline event sync.
- Progressive disclosure: a lean SKILL.md body with on-demand references for low idle token cost.

### Client (`scripts/bitrix24_client.py`)
- Zero-dependency (stdlib only) REST client for webhook and OAuth modes.
- Method allowlist + packs, read/write/destructive risk gates (catalog-accurate), plan→execute,
  idempotency keys, JSONL audit with secret masking, and leaky-bucket rate limiting with backoff.
- Documented error taxonomy and retry policy; HTTPS enforced; positional params for
  order-sensitive methods; `crm.item.*` pagination; REST v3 path support; case-sensitive v2/v3
  method names preserved.
- Optional output economy (`--out compact|summary`, `--max-items`) and `--preflight`
  required-parameter checks.

### Offline worker (`scripts/offline_sync_worker.py`)
- OAuth offline-event sync worker with a handler registry, per-tenant single-instance lock,
  dead-letter queue with re-drive, and automatic token refresh.

### Tooling & CI
- Doc-driven metadata extraction and catalog generators; anti-drift checks (catalog↔dataset,
  chains↔catalog); bundled `required_params.json` / `method_risk.json` sync checks; lint; a
  Python 3.9–3.13 test matrix; and secret scanning.

### Docs
- README quickstart, cross-runtime install (Claude Code, Codex, Gemini, Cursor, Copilot,
  OpenClaw, Hermes), security and trust notes, and region-aware MCP guidance.

## [1.0.0] — 2026-02-14

- Initial public release of the Bitrix24 agent skill.
