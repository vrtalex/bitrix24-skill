# Bitrix24 Agent Skill Pack

Production-grade skill pack to connect AI agents with Bitrix24 REST API quickly and safely.

## Why Teams Choose This Skill

- Fast launch: webhook mode for immediate automation.
- Scale path: OAuth mode for durable multi-tenant integrations.
- Reliability first: retry/backoff and offline queue worker pattern.
- Agent-ready: clear `SKILL.md` + reference playbook for deterministic behavior.
- Minimal footprint: no heavy framework dependency.

## Source Of Truth

Official Bitrix24 REST documentation repository:
- https://github.com/bitrix-tools/b24-rest-docs

Use it as the canonical source for methods, auth rules, events, and limits.

## What Is Included

```text
skills/bitrix24-agent/
  SKILL.md
  references/bitrix24.md
  scripts/bitrix24_client.py
  scripts/offline_sync_worker.py
  agents/openai.yaml
```

## Integration Choice: When To Use What

| Option | Use it when | Avoid it when |
|---|---|---|
| Incoming Webhook | You need fast setup for one portal and internal automation | You need marketplace/local app lifecycle, multi-tenant auth, or app-only event flows |
| OAuth 2.0 App | You need scalable production integration, token lifecycle, app context methods, advanced event scenarios | You only need a quick single-portal script and want minimal setup |
| Outgoing Webhook | You need near real-time push notifications from Bitrix24 to your endpoint | You require guaranteed delivery/replay by default |
| MCP Server | You want agents to generate more accurate Bitrix24 API calls and discover methods/params faster | You treat MCP as runtime transport for production business operations |

Short rule:
- Runtime business actions: `incoming webhook` or `OAuth`.
- Production multi-tenant/event-heavy architecture: `OAuth`.
- Triggering from portal changes: `outgoing webhook` (plus your queue).
- Agent implementation quality boost: `MCP`.

## Requirements

- Python 3.9+
- Bitrix24 portal with REST access
- Credentials for one auth mode

## Quick Start

1. Create env file:

```bash
cp .env.example .env
```

2. Fill `.env`.

Incoming webhook example:

```bash
export B24_DOMAIN="your-portal.bitrix24.com"
export B24_AUTH_MODE="webhook"
export B24_WEBHOOK_USER_ID="1"
export B24_WEBHOOK_CODE="your_webhook_code"
```

OAuth example:

```bash
export B24_DOMAIN="your-portal.bitrix24.com"
export B24_AUTH_MODE="oauth"
export B24_ACCESS_TOKEN="your_access_token"
export B24_REFRESH_TOKEN="your_refresh_token"
export B24_CLIENT_ID="your_client_id"
export B24_CLIENT_SECRET="your_client_secret"
```

3. Load env and run smoke tests:

```bash
source .env
python3 skills/bitrix24-agent/scripts/bitrix24_client.py user.current --params '{}'
python3 skills/bitrix24-agent/scripts/bitrix24_client.py crm.lead.list --params '{"select":["ID","TITLE"],"start":0}'
```

## Practical API Examples

Create a lead:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py crm.lead.add \
  --params '{"fields":{"TITLE":"Skill Demo Lead","NAME":"Agent"}}'
```

Update a lead:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py crm.lead.update \
  --params '{"id":1,"fields":{"COMMENTS":"Updated by agent"}}'
```

Execute batch:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py batch --params '{
  "halt":0,
  "cmd":{
    "lead_list":"crm.lead.list?select[0]=ID&select[1]=TITLE",
    "user":"user.current"
  }
}'
```

Offline event polling:

```bash
python3 skills/bitrix24-agent/scripts/offline_sync_worker.py --once
```

## OpenClaw / Moltbot Connection

This repository is already in Agent Skill layout. The skill path is:

```text
skills/bitrix24-agent
```

OpenClaw:
- Keep this repo as workspace and point skills discovery to `skills/`.
- Or copy skill folder to your global skills directory:

```bash
mkdir -p ~/.openclaw/skills
cp -R skills/bitrix24-agent ~/.openclaw/skills/bitrix24-agent
```

Moltbot:

```bash
mkdir -p ~/.moltbot/skills
cp -R skills/bitrix24-agent ~/.moltbot/skills/bitrix24-agent
```

After copy, restart runtime or refresh skill cache.

## User Scenarios

1. Auto-create a lead from a form submission.
2. Enrich new leads with external profile data.
3. Route leads by custom qualification rules.
4. Trigger follow-up tasks on deal stage changes.
5. Write AI summaries into deal comments.
6. Sync selected CRM entities to external storage.
7. Detect stale deals and trigger escalations.
8. Run daily data reconciliation for missed updates.
9. Build score-based lead prioritization.
10. Execute safe bulk updates via batch calls.
11. Normalize inconsistent contact fields.
12. Build event-driven handoff from sales to delivery.
13. Trigger approval workflows for high-value deals.
14. Keep external systems aligned with task changes.
15. Build no-loss processing with offline queue + DLQ.

## Reliability Model

- API client handles transient failures with retry/backoff.
- Offline worker supports no-loss style processing:
  - pull events,
  - process with retry budget,
  - move poison events to DLQ,
  - clear only acknowledged events.
- Keep event handlers fast and asynchronous.

## Security Checklist

- `.env` stays out of git.
- Never log raw secrets or tokens.
- Keep webhook secret and OAuth credentials private.
- Validate `application_token` for inbound events.
- Use least-privilege permissions/scopes.

## Common Errors

- `Method not found`: wrong method path or webhook parts (`USER_ID`, `WEBHOOK_CODE`).
- `WRONG_AUTH_TYPE`: method requires another auth model (often app/OAuth context).
- `QUERY_LIMIT_EXCEEDED`: too many requests; reduce concurrency and rely on backoff.
- `insufficient_scope`: missing rights/scopes.
- `expired_token`: refresh OAuth token and retry.

## Using As Agent Skill

Point your runtime to:

```text
skills/bitrix24-agent
```

Runtime should load:
- `SKILL.md` as instruction entry,
- `references/bitrix24.md` as implementation playbook,
- scripts for deterministic execution paths.

## License

The Unlicense.
