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
