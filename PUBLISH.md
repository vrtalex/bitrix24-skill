# Publish (Private GitHub)

This repo is already initialized and committed locally on branch `main`.

## 1) Create Private Repository on GitHub

Create an empty private repo in GitHub UI (no README, no .gitignore, no license).

Example name:
- `bitrix24-agent-skill`

## 2) Connect Remote and Push

SSH:

```bash
git remote add origin git@github.com:<your-user>/<your-private-repo>.git
git push -u origin main
```

HTTPS:

```bash
git remote add origin https://github.com/<your-user>/<your-private-repo>.git
git push -u origin main
```

If `origin` already exists:

```bash
git remote set-url origin git@github.com:<your-user>/<your-private-repo>.git
git push -u origin main
```

## 3) Verify Secrets Safety

Before push, check:

```bash
git status --short
git ls-files | rg -n '^\\.env$' || true
```

Expected:
- clean working tree (or only intended changes),
- `.env` is not tracked.

## 4) Optional: Ship Archive

Build a clean source archive from current HEAD:

```bash
mkdir -p dist
git archive --format=tar.gz --output dist/bitrix24-agent-skill-main.tar.gz HEAD
shasum -a 256 dist/bitrix24-agent-skill-main.tar.gz
```
