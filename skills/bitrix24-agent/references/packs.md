# Capability Packs

This skill stays thin by default and expands safely via packs.

## Packs

- `core`: crm + tasks.task + user + events + batch
- `comms`: chats, chat-bots, notifications, telephony
- `automation`: bizproc, robots, workflow templates
- `collab`: workgroups, social feed, collaboration layer
- `content`: disk/files/document flows
- `boards`: scrum/board flows

## Runtime usage

- Default pack: `core`
- Add packs for a call: `--packs core,comms`
- Set global packs: `B24_PACKS="core,comms"`
- Disable packs and use only explicit allowlist: `--packs none --method-allowlist 'user.*'`

## Design rules for new pack entries

1. Add only frequent methods.
2. Keep high-risk write methods explicit and documented.
3. Include at least one read-first chain before write chain.
4. Link every method to official docs.
