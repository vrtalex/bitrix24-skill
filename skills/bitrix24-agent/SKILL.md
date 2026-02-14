---
name: bitrix24-agent
description: Design, implement, debug, and harden integrations between AI agents and Bitrix24 REST API (webhooks, OAuth 2.0, scopes, events, batch, limits, and REST 3.0). Use when asked to connect AI assistants/agents to Bitrix24, automate CRM/tasks/chats, process Bitrix24 events, choose an auth model, or resolve Bitrix24 API errors and performance issues.
---

# Bitrix24 Agent

This skill provides a production workflow for Bitrix24 integrations driven by AI agents.
Use it to avoid common failures: wrong auth model, missing scopes, non-idempotent writes, event loss, and rate-limit collapse.

## Workflow

1. Classify integration mode:
- Single portal/internal integration: prefer incoming webhook.
- Multi-tenant/local app/marketplace: OAuth 2.0 app model.

2. Classify consistency and latency:
- Near real-time reaction: online events.
- Reliable synchronization without loss: offline events and queue polling.

3. Build minimal permission set:
- Determine methods first.
- Then derive required `scope` set.
- Prefer least privilege.

4. Implement request layer:
- Use HTTPS only.
- Parse error codes and `time` block.
- Add retry/backoff for `QUERY_LIMIT_EXCEEDED` and transient `5xx`.
- Add token refresh path for OAuth.
- Add distributed rate limiting when multiple workers share one portal.
- Add OAuth refresh lock/singleflight to prevent concurrent refresh races.

5. Implement guarded write path:
- Read-before-write for critical updates.
- Apply method allowlist policy before every call.
- Idempotency strategy in your app layer.
- Add optimistic concurrency checks to avoid blind overwrite.
- Explicit confirmation for destructive operations.
- Audit logs with method, entity id, status, error code, latency.

6. Harden event handling:
- Verify `application_token` in handlers.
- For offline flow, use `event.offline.get` + `process_id` + `event.offline.clear`.
- Use `auth_connector` to avoid self-trigger loops where supported.
- Implement DLQ (dead-letter queue) for poison events and bounded retries.

7. Validate with contract tests:
- Multi-portal token isolation.
- OAuth refresh race behavior.
- Pagination/full-sync correctness.
- Offline event replay/idempotency and DLQ behavior.

## Guardrails

- Never expose webhook or OAuth secrets in frontend code.
- Store secrets per portal/tenant; never use one global token for all portals.
- Never assume method access without checking scope and user permissions.
- Do not rely on online events as guaranteed delivery (no retries).
- Do not chain nested `batch` calls (not allowed in modern REST versions).
- Prefer REST 3.0 (`/rest/api/`) where applicable; keep v2 fallback for unsupported methods.

## Reference Usage

Read `references/bitrix24.md` before implementation. It includes:
- auth decision matrix and architecture patterns,
- scope and method playbooks,
- error/retry strategy,
- events and sync blueprints,
- security checklist,
- ready-to-use request templates.
- ready-to-run Python utilities in `scripts/`.

Quick section navigation:

```bash
rg -n "^## " references/bitrix24.md
rg -n "QUERY_LIMIT_EXCEEDED|insufficient_scope|expired_token" references/bitrix24.md
rg -n "offline|event\\.bind|event\\.offline" references/bitrix24.md
rg -n "allowlist|DLQ|singleflight|pagination|contract tests" references/bitrix24.md
```

## Scripts

- `scripts/bitrix24_client.py`: request client with retries, rate limit backoff, and optional OAuth refresh callback.
- `scripts/offline_sync_worker.py`: offline queue worker with bounded retries and DLQ output.
