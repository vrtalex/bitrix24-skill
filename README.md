# Bitrix24 Agent Skill Pack

Production-ready skill package for building and hardening AI integrations with Bitrix24:
- auth models (`webhook` / `OAuth 2.0`),
- REST calls (v2/v3),
- retries/backoff/rate-limit handling,
- event pipelines (online/offline),
- operational guardrails (idempotency, DLQ, policy gates).

## What This Repo Includes

- `skills/bitrix24-agent/SKILL.md`: core workflow and guardrails.
- `skills/bitrix24-agent/references/bitrix24.md`: detailed implementation playbook.
- `skills/bitrix24-agent/scripts/bitrix24_client.py`: CLI client for REST calls.
- `skills/bitrix24-agent/scripts/offline_sync_worker.py`: offline event queue worker.

## Repository Structure

```text
skills/bitrix24-agent/
  SKILL.md
  agents/openai.yaml
  references/bitrix24.md
  scripts/bitrix24_client.py
  scripts/offline_sync_worker.py
```

## 15 Practical User Scenarios

1. Auto-create a lead when a new website form submission arrives.
2. Enrich new leads with external data before assignment.
3. Route leads to the right owner based on custom business rules.
4. Create follow-up tasks automatically after deal stage changes.
5. Post AI-generated deal summaries as timeline comments.
6. Sync selected CRM entities to an external data warehouse.
7. Detect stale deals and trigger reminders or escalation tasks.
8. Build a chatbot flow that answers and logs key actions in CRM.
9. Mirror task updates to an external project management system.
10. Validate required fields before permitting critical status transitions.
11. Run nightly reconciliation to fix missed or delayed event updates.
12. Trigger approval workflows when high-value deals are created.
13. Aggregate activity signals and score lead/deal priority.
14. Implement safe bulk updates with batching, retries, and audit logs.
15. Build a resilient offline-event worker for no-loss synchronization.

## Requirements

- Python 3.9+
- Bitrix24 portal with REST access
- Either webhook credentials or OAuth app credentials

## Quick Start (Webhook)

1. Create local env file:

```bash
cp .env.example .env
```

2. Edit `.env` with your portal credentials.

3. Load env and run smoke test:

```bash
set -a
source .env
set +a

python3 skills/bitrix24-agent/scripts/bitrix24_client.py user.current --params '{}'
```

4. CRM write test:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py crm.lead.add \
  --params '{"fields":{"TITLE":"SKILL_TEST Lead","NAME":"Bot"}}'
```

## Quick Start (OAuth)

Set env values:
- `B24_AUTH_MODE=oauth`
- `B24_ACCESS_TOKEN`
- `B24_REFRESH_TOKEN` (optional but recommended)
- `B24_CLIENT_ID` and `B24_CLIENT_SECRET` (required for auto-refresh)

Then:

```bash
set -a
source .env
set +a

python3 skills/bitrix24-agent/scripts/bitrix24_client.py user.current --params '{}' --auto-refresh
```

## Decision Matrix (Webhook / OAuth / Outgoing Webhook / MCP)

| Option | Best for | Tradeoffs |
|---|---|---|
| Incoming Webhook | Fast start on one portal, simple REST automations | Long-lived secret; limited app-context capabilities |
| OAuth App | Multi-tenant apps, advanced events, app lifecycle, robust production setup | More setup complexity (tokens, refresh, install flow) |
| Outgoing Webhook (events to your handler) | Event-driven reactions from portal changes | No retry delivery; handler must be publicly reachable and fast |
| Bitrix24 MCP Server | Better code generation and method discovery for AI development | Developer-assist layer only; not a runtime transport for production calls |

Rule of thumb:
- Runtime data/actions: Incoming Webhook or OAuth.
- Event push trigger: Outgoing Webhook.
- Better AI implementation quality: MCP.

## Quick Start (Outgoing Webhook Events)

1. Create a public HTTPS endpoint (for example, `/b24/events`) in your backend.
2. In Bitrix24, create an outgoing webhook and select target events (for example, deal/task updates).
3. Configure webhook to call your endpoint.
4. In handler, process `application/x-www-form-urlencoded` payload and return `200` quickly.
5. Push heavy logic to internal queue/worker instead of doing it inline.

Minimal handler pattern:

```js
app.post("/b24/events", express.urlencoded({ extended: true }), (req, res) => {
  // 1) Validate request token/signature fields according to your webhook setup
  // 2) Enqueue event for async processing
  // 3) Respond immediately
  res.status(200).send("OK");
});
```

Reliability note:
- Outgoing webhook delivery is not a full retry queue. For strict "no-loss" sync requirements, use app/OAuth context with offline event patterns.

## Event/Queue Tests

`events` and `event.offline.*` require app/OAuth context.

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py events --params '{"FULL": true}'
python3 skills/bitrix24-agent/scripts/offline_sync_worker.py --once
```

## Common Errors

- `Method not found` in webhook mode:
  usually wrong webhook path parts (check user id and secret formatting).
- `WRONG_AUTH_TYPE`:
  method requires app/OAuth context, webhook auth is not enough.
- `QUERY_LIMIT_EXCEEDED`:
  request rate is too high; use retries/backoff and lower concurrency.
- `insufficient_scope` / `INVALID_CREDENTIALS`:
  missing scope or insufficient user permissions in Bitrix24.

## Security Notes

- Keep `B24_WEBHOOK_CODE` as secret only, without `user_id/` prefix.
- Never commit real secrets from `.env` (this repo ignores `.env` by default).
- Do not place webhook or OAuth secrets in frontend code.

## Using the Skill in Agent Runtimes

This repository ships an Agent Skill folder. Point your runtime to:

```text
skills/bitrix24-agent
```

The runtime should load `SKILL.md` and use bundled `references/` and `scripts/`.

## Connect to OpenClaw / Moltbot

This skill is AgentSkills-compatible and works as a normal `SKILL.md` folder.

### OpenClaw

Option A (workspace-local):

```bash
mkdir -p ~/.openclaw/workspace/skills
cp -R skills/bitrix24-agent ~/.openclaw/workspace/skills/bitrix24-agent
```

Option B (current project workspace):
- keep this repo as your active workspace, where the skill already exists at:
  `skills/bitrix24-agent`

Then refresh skills (or restart OpenClaw session/gateway).

### Moltbot

Moltbot loads skills from:
1. `<workspace>/skills` (highest priority)
2. `~/.moltbot/skills`
3. bundled skills

Install globally for Moltbot:

```bash
mkdir -p ~/.moltbot/skills
cp -R skills/bitrix24-agent ~/.moltbot/skills/bitrix24-agent
```

If the same skill name exists in multiple locations, workspace copy takes precedence.
After install, refresh skills or restart Moltbot.

## License

This project is released under The Unlicense (public domain style; unrestricted use/modification/distribution).
