# Phase 8: Config File Support - Research

**Researched:** 2026-02-26
**Domain:** Python argparse + stdlib json — CLI flag defaults from a JSON config file
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**JSON key naming**
- Keys match argparse dest names exactly: `lang`, `psm`, `padding`, `workers`, `force`, `verbose`, `dry_run`, `validate_only`
- Boolean flags use `true`/`false` JSON values (e.g., `"verbose": true`)
- Unknown keys: warn to stderr (`[WARN: unknown config key 'lng']`) but continue — do not abort
- Wrong type for a key (e.g., `"workers": "four"`): print a clear error naming key and expected type (`Error: config key 'workers' expects int, got str`), then exit 1

**Which flags are configurable**
- Excluded (must always be CLI): `--input`, `--output`, `--config`
- Included (all tuning flags): `lang`, `psm`, `padding`, `workers`
- Included (operational flags): `force`, `verbose`, `dry_run`, `validate_only` — technically allowed, though rarely useful to persist
- Config file is flat — no nesting by category, no `extends`/`base` key

**Error messages**
- Missing file: `Error: config file not found: <path>` → stderr, exit 1
- Invalid JSON: `Error: config file contains invalid JSON: <parser message>` → stderr, exit 1 (show the json.JSONDecodeError message for exact location)
- Type error: `Error: config key '<key>' expects <type>, got <type>` → stderr, exit 1
- Style consistent with existing `validate_tesseract()` error pattern

**Verbose config reporting**
- When `--verbose` and `--config` are both active: print a config summary line at startup, before any file processing — e.g., `Config: lang=deu, workers=4 (from myconfig.json)`
- If a CLI flag overrides a config value, note it: `Config: lang=deu → eng (CLI override)`
- Unknown key warnings are always printed to stderr regardless of `--verbose` state (typos must be visible)

### Claude's Discretion

None specified — all decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OPER-04 | `--config PATH` loads CLI flag defaults from a JSON file; any flag specified on the command line overrides the config value | Covered by argparse `set_defaults()` pattern applied before `parse_args()` |
| OPER-05 | If `--config PATH` is specified but the file does not exist or is not valid JSON, pipeline exits with a clear error message before any processing begins | Covered by a dedicated `load_config()` function that runs before `parse_args()` or immediately after, before any heavy work begins |
</phase_requirements>

---

## Summary

Phase 8 is a pure-Python stdlib task. The entire implementation uses `argparse` (already imported), `json` (already imported), `sys` (already imported), and `pathlib.Path` (already imported). No new dependencies are required and no new libraries need to be added to `requirements.txt`.

The canonical pattern for config-file-backed CLI flags in Python is: (1) parse `--config` out of `sys.argv` with a lightweight pre-pass or a separate minimal parser, (2) load and validate the JSON file, (3) call `parser.set_defaults(**config_values)` to inject config values as new argparse defaults, (4) call `parser.parse_args()` normally — CLI flags automatically override the injected defaults because argparse's precedence model is `explicit CLI flag > set_defaults() > argument-level default`. This approach requires zero changes to the existing `add_argument` calls.

The most important design detail is the override-detection mechanism for the verbose config summary line. argparse does not expose which arguments were explicitly supplied by the user vs. filled from defaults. The standard workaround is to compare `vars(args)` against `vars(parser.parse_args([]))` before injecting config defaults, or to collect the config values in a dict and compare them to the final `args` values after parsing. The latter is simpler: after `parse_args()`, compare `args.<key>` against `config_values[key]` — if they differ, the CLI overrode the config.

**Primary recommendation:** Implement a `load_config(path: Path) -> dict` function called in `main()` before the heavy-work block. Apply its output via `parser.set_defaults()` before `parse_args()`. The entire feature requires changes only to `main()` plus a new standalone `load_config()` helper function.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` | stdlib | Parse JSON config file | Already imported in pipeline.py; handles JSONDecodeError with exact location info |
| `argparse` | stdlib | `set_defaults()` for config injection; `parse_known_args()` for `--config` pre-pass | Already imported; `set_defaults()` is the canonical override pattern |
| `pathlib.Path` | stdlib | Config path existence check | Already imported and used throughout |
| `sys` | stdlib | stderr output, exit | Already imported |

### Supporting

None required. All needed libraries are already present in the codebase.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `json` + `set_defaults()` | `configparser` (INI format) | User decided JSON — locked |
| `json` + `set_defaults()` | `tomllib` (TOML, Python 3.11+) | User decided JSON — locked |
| `json` + `set_defaults()` | `click` with auto_envvar_prefix | Would replace argparse — far too invasive |
| `parse_known_args()` pre-pass | `argparse.ArgumentParser` with two-pass parsing | Both work; `parse_known_args()` is cleaner for extracting `--config` before full parse |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Project Structure

No structural changes. All changes are contained within `pipeline.py`:

```
pipeline.py
├── load_config()         # NEW — validates JSON, types, returns clean dict
├── main()                # MODIFIED — two-pass argparse, set_defaults(), verbose summary
└── [all other functions unchanged]
```

### Pattern 1: Two-Pass Argparse with set_defaults()

**What:** A minimal pre-parser extracts `--config` before the full parse. The config is loaded, validated, and injected via `set_defaults()`. Then `parse_args()` runs normally.

**When to use:** When config file support must be transparent to all other argument definitions — no changes to existing `add_argument()` calls.

**Example:**

```python
# Source: Python stdlib argparse docs (set_defaults pattern)
# Step 1: Pre-parse to extract --config path only
pre = argparse.ArgumentParser(add_help=False)
pre.add_argument('--config', type=Path, default=None)
pre_args, _ = pre.parse_known_args()

# Step 2: Load and validate config if --config was supplied
config_values = {}
if pre_args.config is not None:
    config_values = load_config(pre_args.config)  # exits on error

# Step 3: Inject config as defaults into the real parser
if config_values:
    parser.set_defaults(**config_values)

# Step 4: Full parse — CLI flags override set_defaults()
args = parser.parse_args()
```

**Why set_defaults() gives correct precedence:**
argparse precedence order is:
1. Explicit CLI flag (highest)
2. Value from `set_defaults()`
3. `default=` kwarg in `add_argument()` (lowest)

So `--lang eng` on the CLI will override `"lang": "deu"` from the config file, without any additional logic.

### Pattern 2: load_config() Validation Function

**What:** A dedicated function that owns all config loading, file error handling, type checking, and unknown-key warnings. Returns a clean dict ready for `set_defaults()`.

**When to use:** Always — isolates all config-related error handling in one testable unit.

**Type map for validation:**

```python
# Source: pipeline.py existing argparse definitions (verified directly)
CONFIG_TYPES = {
    'lang':          str,
    'psm':           int,
    'padding':       int,
    'workers':       int,
    'force':         bool,
    'verbose':       bool,
    'dry_run':       bool,
    'validate_only': bool,
}
```

**Example:**

```python
def load_config(path: Path) -> dict:
    """Load and validate a JSON config file of flag defaults.

    Returns a dict of validated key→value pairs ready for parser.set_defaults().
    Exits with code 1 on missing file, invalid JSON, or type mismatch.
    Unknown keys emit a stderr warning but do not abort.
    """
    if not path.exists():
        print(f"Error: config file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f"Error: config file contains invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    validated = {}
    for key, value in raw.items():
        if key not in CONFIG_TYPES:
            print(f"[WARN: unknown config key '{key}']", file=sys.stderr)
            continue
        expected = CONFIG_TYPES[key]
        if not isinstance(value, expected):
            # json booleans are ints in Python — bool is subclass of int, check bool first
            actual_type = type(value).__name__
            print(
                f"Error: config key '{key}' expects {expected.__name__}, got {actual_type}",
                file=sys.stderr,
            )
            sys.exit(1)
        validated[key] = value

    return validated
```

**Critical Python type subtlety:** `bool` is a subclass of `int` in Python. `isinstance(True, int)` returns `True`. For keys that expect `int` (like `workers`), a config value of `true` would pass the `isinstance(value, int)` check but should be rejected. The type check must handle this: for `int`-typed keys, also check `not isinstance(value, bool)`. Conversely, for `bool`-typed keys, `isinstance(value, bool)` is unambiguous.

**Corrected type check for int keys:**

```python
if expected is int:
    if not isinstance(value, int) or isinstance(value, bool):
        # reject — bool passes isinstance(v, int) but is not a valid int config value
        ...
elif not isinstance(value, expected):
    ...
```

### Pattern 3: Verbose Config Summary Line

**What:** After `parse_args()`, if both `--verbose` and `--config` are active, print a summary of which config values are in effect and which were overridden by CLI.

**When to use:** Only when `args.verbose and args.config is not None`.

**Override detection approach:**

```python
# config_values: dict returned by load_config() — the values from the file
# args: the fully parsed Namespace — may have been overridden by CLI

if args.verbose and pre_args.config is not None and config_values:
    parts = []
    for key, file_val in config_values.items():
        cli_val = getattr(args, key)
        if cli_val != file_val:
            parts.append(f"{key}={file_val} → {cli_val} (CLI override)")
        else:
            parts.append(f"{key}={cli_val}")
    config_name = pre_args.config.name
    print(f"Config: {', '.join(parts)} (from {config_name})")
```

### Anti-Patterns to Avoid

- **Parsing --config inside parse_args():** argparse processes all arguments together; you cannot conditionally inject defaults mid-parse. The two-pass approach (pre-parser + set_defaults) is the only clean solution.
- **Modifying add_argument() calls:** No existing argument definition needs to change. set_defaults() overrides at a higher precedence level than `default=` kwargs without touching them.
- **Using argparse.FileType for --config:** FileType opens the file immediately but gives a stream, not a Path. The existing codebase uses Path throughout; stay consistent.
- **Validating config types against argparse internals:** Don't try to extract type info from parser._actions. Maintain CONFIG_TYPES as an explicit dict — it's simpler and self-documenting.
- **Collecting bool flags as JSON strings:** The user decided `"verbose": true` (boolean), not `"verbose": "true"` (string). The validator must enforce this.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Default precedence (config vs. CLI) | Custom merge logic in main() | `parser.set_defaults()` | argparse's built-in precedence handles this exactly — CLI > set_defaults > add_argument default |
| JSON parsing with error location | Custom parser | `json.JSONDecodeError` message from stdlib | JSONDecodeError already includes line/column info for the parser message |
| Type coercion of config values | Auto-convert string "4" to int | Explicit type check + rejection | User decided wrong type is an error, not auto-coerced |

**Key insight:** The entire feature is a thin wrapper around `json.loads()` and `parser.set_defaults()`. Any custom merge logic or type-coercion machinery is unnecessary complexity.

## Common Pitfalls

### Pitfall 1: bool-as-int Confusion

**What goes wrong:** `isinstance(True, int)` returns `True` in Python because `bool` is a subclass of `int`. An `int`-typed config key (e.g., `workers`) would silently accept `true`/`false` JSON booleans as valid integers.

**Why it happens:** Python's type hierarchy. `True == 1` and `False == 0`.

**How to avoid:** For `int`-typed keys, check `isinstance(value, int) and not isinstance(value, bool)`. For `bool`-typed keys, `isinstance(value, bool)` is sufficient and correctly rejects integers.

**Warning signs:** A user passes `"workers": true` and gets 1 worker silently instead of an error.

### Pitfall 2: --config Parsed Twice, Values Diverge

**What goes wrong:** The pre-parser and main parser both define `--config`. If they use different defaults or types, the pre-parse result and the final `args.config` may differ.

**Why it happens:** `parse_known_args()` on the pre-parser returns its own Namespace; the main parser returns a separate Namespace.

**How to avoid:** After `parse_args()`, use `args.config` (from main parser) consistently. Use `pre_args.config` only for the initial load. Both should agree because the same `sys.argv` is parsed. Alternatively, pass `--config` value through to set_defaults only and let main parser own the final `args.config`.

**Warning signs:** `pre_args.config` is a Path but `args.config` is None (forgot to add `--config` to main parser).

### Pitfall 3: Verbose Summary Printed Too Early or Too Late

**What goes wrong:** The config summary line appears after file result lines instead of before any processing, or it appears before validate_tesseract() runs and confuses the operator when Tesseract then fails.

**Why it happens:** Order of operations in main() not carefully considered.

**How to avoid:** Per the locked decision, print the config summary "at startup, before any file processing." The correct position is: after `parse_args()`, after `validate_tesseract()`, before `discover_tiffs()` or any heavy work. This matches the existing output order: Tesseract errors first, then setup, then file results.

**Warning signs:** Config summary line appears interleaved with file result lines.

### Pitfall 4: dry_run Key vs. dry-run Argparse Dest

**What goes wrong:** argparse converts `--dry-run` to `args.dry_run` (hyphen → underscore), but a user writing the config file might use `"dry-run"` as the key.

**Why it happens:** argparse's automatic dest conversion is not obvious to users.

**How to avoid:** The user decision is locked: keys match argparse dest names exactly, meaning `dry_run` (with underscore). The error wording for unknown keys (`[WARN: unknown config key 'dry-run']`) will surface the mismatch to the user naturally if they use the hyphenated form. Document the dest names clearly in any example config.

**Warning signs:** `dry-run` in config file silently does nothing (treated as unknown key with warning).

### Pitfall 5: Config Applied After validate_tesseract()

**What goes wrong:** `lang` from the config file is not applied before `validate_tesseract(args.lang)` because config loading happens after `parse_args()` returns.

**Why it happens:** If `set_defaults()` is called before `parse_args()`, the config `lang` value is properly included in `args.lang` when `validate_tesseract()` runs.

**How to avoid:** The correct order is: pre-parse for `--config` → load_config() → `set_defaults()` → `parse_args()` → `validate_tesseract(args.lang)`. This ensures the config-supplied `lang` is in effect when Tesseract validation runs.

**Warning signs:** User sets `"lang": "fra"` in config but `validate_tesseract()` checks `deu` (the argparse default) instead.

## Code Examples

Verified patterns from stdlib argparse documentation and direct inspection of pipeline.py:

### Full Integration Sketch for main()

```python
# Source: Python stdlib argparse docs (set_defaults), pipeline.py (existing pattern)

def main() -> None:
    # -----------------------------------------------------------------------
    # Step 0: Pre-parse to extract --config before the full parse
    # -----------------------------------------------------------------------
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument('--config', type=Path, default=None)
    pre_args, _ = pre.parse_known_args()

    # -----------------------------------------------------------------------
    # Step 1: Build full parser (unchanged from existing code)
    # -----------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description='Batch OCR: TIFF folder → ALTO 2.1 XML'
    )
    parser.add_argument('--config', type=Path, default=None, ...)
    # ... all existing add_argument() calls unchanged ...

    # -----------------------------------------------------------------------
    # Step 2: Load config and inject as defaults
    # -----------------------------------------------------------------------
    config_values = {}
    if pre_args.config is not None:
        config_values = load_config(pre_args.config)  # exits on error
    if config_values:
        parser.set_defaults(**config_values)

    # -----------------------------------------------------------------------
    # Step 3: Full parse — CLI flags override set_defaults()
    # -----------------------------------------------------------------------
    args = parser.parse_args()

    # ... existing n_workers, load_xsd(), validate_tesseract() ...

    # -----------------------------------------------------------------------
    # Step 4: Verbose config summary (if applicable)
    # -----------------------------------------------------------------------
    if args.verbose and args.config is not None and config_values:
        parts = []
        for key, file_val in config_values.items():
            cli_val = getattr(args, key)
            if cli_val != file_val:
                parts.append(f"{key}={file_val} → {cli_val} (CLI override)")
            else:
                parts.append(f"{key}={cli_val}")
        print(f"Config: {', '.join(parts)} (from {args.config.name})")

    # ... rest of main() unchanged ...
```

### CONFIG_TYPES Constant and Placement

```python
# Source: pipeline.py argparse definitions (verified directly)
# Place near top of pipeline.py after POSITIONAL_TAGS and constants

CONFIG_TYPES: dict[str, type] = {
    'lang':          str,
    'psm':           int,
    'padding':       int,
    'workers':       int,
    'force':         bool,
    'verbose':       bool,
    'dry_run':       bool,
    'validate_only': bool,
}
```

### Error Message Consistency Check

Existing validate_tesseract() pattern (from pipeline.py line 483):
```python
print(
    "ERROR: Tesseract OCR is not installed or not on PATH.\n"
    "  macOS:  brew install tesseract\n"
    "  Ubuntu: apt install tesseract-ocr",
    file=sys.stderr,
)
sys.exit(1)
```

The CONTEXT.md decisions use `Error:` (capital E, colon) — note the existing code uses `ERROR:` (all caps). The locked decision says style consistent with `validate_tesseract()`. Clarify: the context specifies lowercase-`r` `Error:` format. The planner should match the exact capitalization from the locked decisions verbatim (`Error: config file not found: <path>`), not the existing `ERROR:` pattern which uses all-caps.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hand-written config parsers, INI files | `argparse.set_defaults()` + stdlib json | Python 3.2+ | Zero-dependency, precedence-correct |
| `configargparse` third-party library | stdlib-only (argparse + json) | N/A for this project | User decided no new deps; stdlib is sufficient |

**Deprecated/outdated:**
- `configparser` (INI format): Works but user decided on JSON — do not use.
- `argparse.Namespace` direct mutation after parse: Fragile — breaks argparse internals. Use `set_defaults()` instead.

## Open Questions

1. **Error capitalization consistency**
   - What we know: CONTEXT.md says `Error: config file not found:` (capital E, lowercase r); existing codebase uses `ERROR:` (all caps) in `validate_tesseract()` and `ERROR:` elsewhere
   - What's unclear: Should Phase 8 use `Error:` per the locked decision or `ERROR:` per codebase convention?
   - Recommendation: Use the exact wording from the locked decisions (`Error:` with capital E, lowercase r). The locked decisions take precedence over existing codebase pattern. The planner should call this out explicitly in the plan.

2. **Position of verbose config summary relative to validate_tesseract()**
   - What we know: Config summary should appear "before any file processing"; validate_tesseract() runs before discover_tiffs()
   - What's unclear: Should config summary appear before or after validate_tesseract()?
   - Recommendation: Print config summary AFTER validate_tesseract(). If Tesseract is missing, the run fails immediately and the config summary is noise. Printing it after validate_tesseract() but before discover_tiffs() ensures it only appears in runs that will actually proceed.

## Sources

### Primary (HIGH confidence)

- Python 3 stdlib argparse docs — `set_defaults()`, `parse_known_args()` — verified against https://docs.python.org/3/library/argparse.html
- Python 3 stdlib json docs — `json.loads()`, `json.JSONDecodeError` — verified against https://docs.python.org/3/library/json.html
- `/Users/zu54tav/Zeitschriften-OCR/pipeline.py` — direct inspection of existing argparse definitions, imports, and error patterns

### Secondary (MEDIUM confidence)

- `.planning/phases/08-config-file-support/08-CONTEXT.md` — user locked decisions on key naming, error format, verbose output

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no new dependencies; verified existing imports
- Architecture: HIGH — argparse `set_defaults()` is well-documented stdlib behavior; two-pass parse is a well-known pattern
- Pitfalls: HIGH — bool-is-int subclass is a documented Python behavior; other pitfalls verified against pipeline.py source directly

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stdlib APIs are stable; 30-day validity)
