# Bitrix24 Agent Skill Pack

Minimal skill package for AI-agent integrations with Bitrix24 REST API.

## Included

```text
skills/bitrix24-agent/
  SKILL.md
  references/bitrix24.md
  scripts/bitrix24_client.py
  scripts/offline_sync_worker.py
  agents/openai.yaml
```

## Requirements

- Python 3.9+
- Bitrix24 portal with REST access
- Webhook or OAuth credentials

## Quick Start

1. Create env file:

```bash
cp .env.example .env
```

2. Fill `.env`.

Webhook mode example:

```bash
export B24_DOMAIN="your-portal.bitrix24.com"
export B24_AUTH_MODE="webhook"
export B24_WEBHOOK_USER_ID="1"
export B24_WEBHOOK_CODE="your_webhook_code"
```

OAuth mode example:

```bash
export B24_DOMAIN="your-portal.bitrix24.com"
export B24_AUTH_MODE="oauth"
export B24_ACCESS_TOKEN="your_access_token"
export B24_REFRESH_TOKEN="your_refresh_token"
export B24_CLIENT_ID="your_client_id"
export B24_CLIENT_SECRET="your_client_secret"
```

3. Load env and run API call:

```bash
source .env
python3 skills/bitrix24-agent/scripts/bitrix24_client.py user.current --params '{}'
```

4. Optional offline worker:

```bash
python3 skills/bitrix24-agent/scripts/offline_sync_worker.py --once
```

## Common Errors

- `Method not found`: wrong webhook `USER_ID` or `WEBHOOK_CODE`.
- `WRONG_AUTH_TYPE`: method requires OAuth/app context.
- `QUERY_LIMIT_EXCEEDED`: too many requests; retry with backoff.
- `expired_token`: refresh access token.

## Security

- `.env` is ignored by git.
- Never commit secrets.
- Validate `application_token` in event handlers.

## License

The Unlicense.
