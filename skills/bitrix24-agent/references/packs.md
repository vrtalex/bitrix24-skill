# Capability Packs

This skill stays thin by default and expands safely via packs.

## Token-Efficient Loading Order

Use this exact order:

1. Open this file (`packs.md`).
2. Open one `catalog-<pack>.md`.
3. Open `chains-<pack>.md` only if workflow detail is needed.
4. Open `bitrix24.md` only for protocol-level troubleshooting.

Context budget:

- default: max 2 files before first action,
- max 1 active pack unless task explicitly spans multiple domains,
- keep `core` as default pack.

## Packs

- `core`: crm + tasks.task + user + events + batch
- `comms`: chats, chat-bots, notifications, telephony
- `automation`: bizproc, robots, workflow templates
- `collab`: workgroups, social feed, collaboration layer
- `content`: disk/files/document flows
- `boards`: scrum/board flows
- `commerce`: orders, payments, deliveries, product catalog
- `services`: booking, calendar, time-management
- `platform`: ai, entity storage, biconnector data layer
- `sites`: landing/site/page operations
- `compliance`: user consents and sign-b2e document tails
- `diagnostics`: method availability, scopes, features, event catalog checks
- `bots`: chat-bot construction (imbot.v2 — bots, commands, chat messages)
- `booking`: bookings, resources, slots, client types
- `mail`: mailboxes and email messages
- `templates`: recurring task templates (tasks.template)

## Runtime usage

- Default pack: `core`
- Add packs for a call: `--packs core,comms`
- Set global packs: `B24_PACKS="core,commerce"`
- Disable packs and use only explicit allowlist: `--packs none --method-allowlist 'user.*'`

## Catalog columns

Each `catalog-<pack>.md` row is `Method | Risk | Scope | Required | Deprecated | Docs`,
derived from the official docs (regenerate with `tools/enrich_catalogs.py`):

- `Scope` — OAuth scope(s) the method needs (e.g. `crm`, `task`, `imopenlines`); `-` for scopeless system/event methods. Use it to pick scopes and to diagnose `insufficient_scope`.
- `Required` — required parameter names. Pass these on the first call to avoid a failed round-trip; you usually don't need to open the method page.
- `Deprecated` — empty if current; `→ replacement` if the docs deprecated it. Prefer the replacement (e.g. `crm.lead.*` → `crm.item.*`, `imbot.*` → `imbot.v2.*`).

## Coverage: head + tail

Catalogs intentionally list only the frequent "head" methods. For anything not listed,
discover it at runtime instead of guessing: `method.get` / `methods` / `scope`
(`diagnostics` pack), then call with `--allow-unlisted`. This keeps catalogs small while
still reaching the full API surface.

## Risk levels in catalogs

The `Risk` column in every `catalog-<pack>.md` uses a controlled vocabulary that maps to client confirmation gates:

- `read` — no confirmation needed.
- `write` — requires `--confirm-write` (and `--require-plan`/`B24_REQUIRE_PLAN` if enforced).
- `destructive` — requires `--confirm-destructive`.
- `mixed` — used only for `batch`: its effective risk is the highest risk among its sub-commands, which the client computes at runtime by inspecting `cmd`. A `batch` containing a destructive sub-command is gated as destructive.

## Parameter encoding (JSON vs positional)

- Pass most methods a JSON object via `--params '{"filter":{...},"fields":{...}}'`; the client sends it as a JSON body, which Bitrix24 recommends for nested structures.
- A few order-sensitive methods (e.g. `task.commentitem.add`, `task.checklistitem.complete`) require a **positional array**, not a named object. Pass `--params '[123, {"POST_MESSAGE":"text"}]'` (a JSON array). See `bitrix24.md` → "Data encoding".

## Design rules for new pack entries

1. Add only frequent methods.
2. Keep high-risk write methods explicit and documented.
3. Include at least one read-first chain before write chain.
4. Link every method to official docs.
5. Keep each catalog short; move detail to chains.
