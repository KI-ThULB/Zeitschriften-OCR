# Phase 8: Config File Support - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `--config <path>` flag that reads a JSON file of flag defaults. CLI flags always take silent precedence over config values. Omitting `--config` is a no-op — all existing defaults are unchanged. Missing or invalid config files exit early with a clear error before any TIFF is read or processed.

</domain>

<decisions>
## Implementation Decisions

### JSON key naming
- Keys match argparse dest names exactly: `lang`, `psm`, `padding`, `workers`, `force`, `verbose`, `dry_run`, `validate_only`
- Boolean flags use `true`/`false` JSON values (e.g., `"verbose": true`)
- Unknown keys: warn to stderr (`[WARN: unknown config key 'lng']`) but continue — do not abort
- Wrong type for a key (e.g., `"workers": "four"`): print a clear error naming key and expected type (`Error: config key 'workers' expects int, got str`), then exit 1

### Which flags are configurable
- Excluded (must always be CLI): `--input`, `--output`, `--config`
- Included (all tuning flags): `lang`, `psm`, `padding`, `workers`
- Included (operational flags): `force`, `verbose`, `dry_run`, `validate_only` — technically allowed, though rarely useful to persist
- Config file is flat — no nesting by category, no `extends`/`base` key

### Error messages
- Missing file: `Error: config file not found: <path>` → stderr, exit 1
- Invalid JSON: `Error: config file contains invalid JSON: <parser message>` → stderr, exit 1 (show the json.JSONDecodeError message for exact location)
- Type error: `Error: config key '<key>' expects <type>, got <type>` → stderr, exit 1
- Style consistent with existing `validate_tesseract()` error pattern

### Verbose config reporting
- When `--verbose` and `--config` are both active: print a config summary line at startup, before any file processing — e.g., `Config: lang=deu, workers=4 (from myconfig.json)`
- If a CLI flag overrides a config value, note it: `Config: lang=deu → eng (CLI override)`
- Unknown key warnings are always printed to stderr regardless of `--verbose` state (typos must be visible)

</decisions>

<specifics>
## Specific Ideas

- Error wording should feel consistent with `validate_tesseract()` — short, imperative, actionable
- The config summary line (verbose) appears once at the top before file result lines, not mixed in

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-config-file-support*
*Context gathered: 2026-02-26*
