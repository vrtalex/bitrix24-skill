# Developer tools (not part of the runtime skill)

These scripts are **development/CI only**. The runtime skill (`skills/bitrix24-agent/`)
stays zero-dependency and never imports anything from here.

## API metadata source (pinned)

The catalog enrichment and the anti-drift CI check are derived from the official
Bitrix24 REST documentation:

- Source repo: `https://github.com/bitrix-tools/b24-rest-docs` (mirror of `bitrix24/b24restdocs`)
- Pinned commit: `03b915036ab2c51b7d5f21562282761e3231d510`

To refresh against a newer docs revision:

```bash
git clone --depth 1 https://github.com/bitrix-tools/b24-rest-docs.git /tmp/b24-rest-docs
( cd /tmp/b24-rest-docs && git rev-parse HEAD )   # record this commit hash above
python3 tools/extract_api_metadata.py --docs /tmp/b24-rest-docs/api-reference \
        --out tools/api_metadata.json
```

`extract_api_metadata.py` emits only language-neutral identifiers/flags
(method name, scope codes, required-parameter names, deprecated flag + replacement,
doc path) — never documentation prose. Review the resulting diff before committing:
the extractor is a proposal, a human curates it.

## Tooling

- `extract_api_metadata.py` — parse docs → `api_metadata.json` (dataset).
- `verify_catalogs.py` — anti-drift: catalog methods must exist (unknown → fail);
  docs-deprecated methods are warnings. Run in CI.
- `enrich_catalogs.py` — regenerate the `Scope/Required/Deprecated` columns and
  canonical doc URLs in every catalog from the dataset (idempotent).
- `gen_required_params.py` — regenerate the bundled `scripts/required_params.json`
  (catalog methods with required params) used by the client's `--preflight` check.
  Re-run after catalog changes.
- `gen_method_risk.py` — regenerate the bundled `scripts/method_risk.json` (per-method
  read/write/destructive from the catalog Risk column) so the client's confirmation gates
  match the catalogs exactly. Re-run after catalog changes.
- `token_report.py` — static lean-load footprint (bytes + ~tokens).

## Token economy

Two budgets to keep small:

1. **Input (context):** measured by `token_report.py` — the worst-case lean load is
   `packs.md` + the largest catalog. Track this so enrichment never bloats context.
2. **Output (runtime, the end-user's tokens):** measured live, not offline. Methodology:
   run a fixed set of ~20 representative tasks through the agent and record output
   tokens (CLI stdout the agent reads) and whether each task completed. The catalog
   `Required`/`Scope`/`Deprecated` columns reduce this by removing doc-page lookups and
   first-call failures. Compare against a baseline before flipping any output default.

