# Bitrix24 Agent Skill Pack

Compact, production-oriented skill pack for connecting AI agents to Bitrix24 REST.

## Why this pack

- Fast start for real API calls.
- Safe-by-default execution with allowlist, risk confirmations, and audit log.
- Modular capability packs instead of one oversized monolith.
- Works with webhook and OAuth flows.

## Official docs source

- Main documentation repo: https://github.com/bitrix24/b24restdocs
- MCP docs: https://github.com/bitrix24/b24restdocs/blob/main/sdk/mcp.md

## Project layout

```text
skills/bitrix24-agent/
  SKILL.md
  references/
    bitrix24.md
    packs.md
    catalog-*.md
    chains-*.md
  scripts/
    bitrix24_client.py
    offline_sync_worker.py
  agents/openai.yaml
```

## Auth model: when to use what

| Option | Use when | Not ideal when |
|---|---|---|
| Incoming webhook | One portal, quick internal automation | Multi-tenant app model, app-context-only methods |
| OAuth app | Multi-portal scaling, app lifecycle, controlled token rotation | Very small one-portal scripts where setup speed matters most |
| Outgoing webhook | Need push trigger from portal events to your handler | You need guaranteed retry/replay out of the box |
| MCP server | Need better method/field discovery for agent generation quality | You treat MCP as transactional runtime for business writes |

Short rule:
- Runtime writes: webhook or OAuth.
- Cross-portal product: OAuth.
- Event trigger entrypoint: outgoing webhook + your queue.
- Better agent method accuracy: MCP.

## Capability packs (recommended model)

Instead of one giant allowlist, this repo uses packs.
Each pack is a small method set + short recipes.

| Pack | Focus |
|---|---|
| `core` | CRM + tasks.task + user + events + batch |
| `comms` | Chats, chat-bots, messaging, telephony |
| `automation` | Bizproc/robots/templates |
| `collab` | Workgroups/socialnetwork/feed-style collaboration |
| `content` | Disk/files/document flows |
| `boards` | Scrum/board methods |

Pack docs:
- Index: `skills/bitrix24-agent/references/packs.md`
- Catalogs: `skills/bitrix24-agent/references/catalog-*.md`
- Chains: `skills/bitrix24-agent/references/chains-*.md`

## Token-efficient usage with agents

For best quality/cost ratio, tell your agent to follow this mode:

1. Start with `core` pack only.
2. Read `references/packs.md` and one `catalog-<pack>.md` first.
3. Open `chains-<pack>.md` only when implementation flow is required.
4. Open `references/bitrix24.md` only for auth/limits/error deep-dive.
5. Return concise answers first, then expand only on request.

## If the skill does not cover a Bitrix24 function

1. Verify method in official docs (`bitrix24/b24restdocs`) and required scope.
2. Run it once in controlled mode:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py <method> \
  --params '<json>' \
  --allow-unlisted \
  --confirm-write
```

3. If it is stable and useful, add it to the right pack:
- update `skills/bitrix24-agent/references/catalog-<pack>.md`
- add/update a recipe in `skills/bitrix24-agent/references/chains-<pack>.md`
- extend allowlist patterns in `skills/bitrix24-agent/scripts/bitrix24_client.py` (`PACK_METHOD_ALLOWLIST`)
4. Re-run smoke checks and commit.

## Quick start

1. Create env:

```bash
cp .env.example .env
source .env
```

2. Fill `.env`.

Webhook example:

```bash
export B24_DOMAIN="your-portal.example"
export B24_AUTH_MODE="webhook"
export B24_WEBHOOK_USER_ID="1"
export B24_WEBHOOK_CODE="your_webhook_secret_without_user_id_prefix"
```

OAuth example:

```bash
export B24_DOMAIN="your-portal.example"
export B24_AUTH_MODE="oauth"
export B24_ACCESS_TOKEN="your_access_token"
export B24_REFRESH_TOKEN="your_refresh_token"
export B24_CLIENT_ID="your_client_id"
export B24_CLIENT_SECRET="your_client_secret"
```

3. Smoke tests:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py user.current --params '{}'
python3 skills/bitrix24-agent/scripts/bitrix24_client.py crm.lead.list --params '{"select":["ID","TITLE"],"start":0}'
```

## Pack-enabled CLI usage

Default active pack: `core`.

List packs:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py user.current --params '{}' --list-packs
```

Enable additional packs for current call:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py im.message.add \
  --params '{"DIALOG_ID":"chat1","MESSAGE":"hello"}' \
  --packs core,comms \
  --confirm-write
```

Enable packs globally in env:

```bash
export B24_PACKS="core,comms"
```

Disable packs and rely only on explicit allowlist:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py user.current --params '{}' --packs none --method-allowlist 'user.*'
```

## Practical API examples

Create lead:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py crm.lead.add \
  --params '{"fields":{"TITLE":"Skill Demo Lead","NAME":"Agent"}}' \
  --confirm-write
```

Update lead:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py crm.lead.update \
  --params '{"id":1,"fields":{"COMMENTS":"Updated by agent"}}' \
  --confirm-write
```

Batch call:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py batch --params '{
  "halt":0,
  "cmd":{
    "lead_list":"crm.lead.list?select[0]=ID&select[1]=TITLE",
    "user":"user.current"
  }
}' --confirm-write
```

Offline events worker:

```bash
python3 skills/bitrix24-agent/scripts/offline_sync_worker.py --once
```

## OpenClaw / Moltbot

Skill path in this repo:

```text
skills/bitrix24-agent
```

OpenClaw:

```bash
mkdir -p ~/.openclaw/skills
cp -R skills/bitrix24-agent ~/.openclaw/skills/bitrix24-agent
```

Moltbot:

```bash
mkdir -p ~/.moltbot/skills
cp -R skills/bitrix24-agent ~/.moltbot/skills/bitrix24-agent
```

Restart runtime or refresh skill cache.

## User scenarios (short list)

1. Create lead from external form.
2. Enrich lead with external data.
3. Auto-route lead by score.
4. Create task on deal stage change.
5. Write AI summary to CRM comments.
6. Bulk update entities with guarded batch.
7. Sync selected CRM fields to external DB.
8. Detect stale deals and escalate.
9. Recover missed updates with offline events.
10. Trigger bizproc workflow from CRM event.
11. Send notification to chat on task changes.
12. Register bot command and return structured answer.
13. Manage workgroup metadata and members flow.
14. Upload and attach files to process entities.
15. Run scrum board updates from external triggers.

## Reliability and safety

- Schema validation for method + params.
- Allowlist + capability packs.
- Risk gate flags:
  - `--confirm-write`
  - `--confirm-destructive`
- Retry/backoff for transient API overload.
- Optional OAuth auto-refresh callback.
- JSONL audit trail (default: `.runtime/bitrix24_audit.jsonl`).

## Security checklist

- Keep `.env` out of git.
- Never expose webhook/OAuth secrets in client-side code.
- Verify `application_token` in inbound handlers.
- Keep scopes minimal.
- Use `--allow-unlisted` only as controlled exception.

## Common errors

- `Method not found`: wrong method/path/auth URL format.
- `WRONG_AUTH_TYPE`: method requires a different auth context.
- `QUERY_LIMIT_EXCEEDED`: too much request intensity.
- `insufficient_scope`: missing scopes/permissions.
- `expired_token`: refresh OAuth token and retry.
