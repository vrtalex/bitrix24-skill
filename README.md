# Bitrix24 Agent Skill Pack

Production-ready skill package for building and hardening AI integrations with Bitrix24:
- auth models (`webhook` / `OAuth 2.0`),
- REST calls (v2/v3),
- retries/backoff/rate-limit handling,
- event pipelines (online/offline),
- operational guardrails (idempotency, DLQ, policy gates).

## Repository Structure

```text
skills/bitrix24-agent/
  SKILL.md
  agents/openai.yaml
  references/bitrix24.md
  scripts/bitrix24_client.py
  scripts/offline_sync_worker.py
```

## Quick Start

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

4. CRM test:

```bash
python3 skills/bitrix24-agent/scripts/bitrix24_client.py crm.lead.add \
  --params '{"fields":{"TITLE":"SKILL_TEST Lead","NAME":"Bot"}}'
```

## Important Notes

- Keep `B24_WEBHOOK_CODE` as secret only, without `user_id/` prefix.
- Methods like `events` and `event.offline.*` require app/OAuth context (not plain webhook auth).
- Never commit real secrets from `.env` (this repo ignores `.env` by default).
