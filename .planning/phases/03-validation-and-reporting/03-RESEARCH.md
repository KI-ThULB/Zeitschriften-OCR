# Phase 3: Validation and Reporting - Research

**Researched:** 2026-02-25
**Domain:** lxml XSD validation, ALTO 2.1 schema, Python JSON reporting
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Schema sourcing
- XSD bundled in the repo at `schemas/alto-2-1.xsd` — no network required at runtime
- Validate that the XSD is loadable at startup (before any TIFF is processed); fail fast with a clear error if the file is missing or corrupt
- If the XSD file is missing at runtime (e.g. deleted after startup check), skip validation, emit a warning, and continue — do not abort the batch

#### Validation output
- Record first lxml validation error per file only (not all cascading errors)
- All violations (XSD and coordinate) go into the JSON summary report only — no separate violations log file
- Coordinate check: flag any element where `HPOS + WIDTH > page_width` OR `VPOS + HEIGHT > page_height` (strict — any bleed outside declared page bounds)
- Files with validation violations get status `ocr_ok, validation_warnings` — not failed, not silently ok. Operator decides whether to proceed with Goobi ingest.

#### Report format and location
- Written to `output_dir/report_TIMESTAMP.json` — timestamped, alongside the JSONL error log, never overwritten
- Per-file record fields: `input_path`, `output_path`, `duration_seconds`, `word_count`, `error_status`, `schema_valid` (bool), `coord_violations` (list of violation description strings)
- Run-level summary at top of report: `total_files`, `processed`, `skipped`, `failed_ocr`, `validation_warnings`, `total_duration_seconds`
- Pretty-printed with 2-space indentation
- Report written only if at least one file was processed or validated (pure skip runs produce no report)

#### Validation timing
- Separate post-processing pass after `run_batch()` completes — clean separation, OCR parallelism unaffected, validation pass can run independently
- `--validate-only` flag: skip OCR, validate existing output files and produce a report. Enables re-validation without re-running OCR.
- Final status line format: `Done: N processed, M skipped, P failed, Q validation warnings` — extends the existing Phase 2 format

### Claude's Discretion
- The lxml validator call pattern and error extraction from `etree.XMLSchema.error_log`
- Page dimension extraction from the ALTO `<Page>` element attributes
- How to handle ALTO files that are missing `<Page>` dimensions (probably skip coordinate check with a note)
- Exact structure of `coord_violations` entries (likely `"HPOS+WIDTH=X > page_width=Y at String CONTENT"`)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VALD-01 | Validate each ALTO XML output against the ALTO 2.1 XSD schema using lxml; log schema violations per file without aborting the batch | lxml XMLSchema API confirmed; namespace-adapted XSD required (see critical finding below) |
| VALD-02 | Check that all word bounding boxes in each ALTO file fall within page dimensions; log coordinate violations per file without aborting | ALTO Page element `WIDTH`/`HEIGHT` attributes confirmed; String element `HPOS`/`VPOS`/`WIDTH`/`HEIGHT` confirmed |
| VALD-03 | Write a per-run summary report as JSON containing for each file: input path, output path, processing duration (seconds), word count, and error status | Python stdlib `json` module; `json.dump()` with `indent=2` covers all requirements |
</phase_requirements>

---

## Summary

Phase 3 adds a post-OCR quality layer: XSD schema validation and a JSON summary report. The work is entirely additive — no changes to `process_tiff()`, `run_batch()`, or any existing output format. The validation pass runs after `run_batch()` returns, keeping it decoupled from parallel OCR execution.

The most important finding is a **namespace mismatch** between the official ALTO 2.1 XSD and the project's output. The official `alto-2-1.xsd` (from `github.com/altoxml/schema`) uses `targetNamespace="http://www.loc.gov/standards/alto/ns-v2#"`, but this project's output files use `http://schema.ccs-gmbh.com/ALTO` — the legacy CCS-GmbH namespace required by Goobi/Kitodo. Validating project output against the official XSD will fail on every file with a namespace error. The bundled `schemas/alto-2-1.xsd` must have its `targetNamespace` and default namespace declaration changed to `http://schema.ccs-gmbh.com/ALTO`.

The lxml `XMLSchema` API is stable, well-documented, and exactly suited to this task. The `error_log` accumulation bug (lxml < 3.3.2) is irrelevant because the project pins `lxml>=5.3.0`. `error_log.last_error` (after a failed `validate()` call) gives the first error cleanly. JSON reporting uses Python's stdlib `json.dump()` with `indent=2` — no additional library needed.

**Primary recommendation:** Bundle a namespace-adapted copy of the official ALTO 2.1 XSD at `schemas/alto-2-1.xsd`; implement `validate_alto_file()` with lxml `XMLSchema.validate()` + `error_log.last_error`; implement `validate_batch()` as a post-`run_batch()` pass; write report with `json.dump(..., indent=2)`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lxml | >=5.3.0 (already in requirements.txt) | XSD schema loading and XML validation | Only Python XML library with native libxml2 XSD validation; `etree.XMLSchema` is the canonical API |
| json (stdlib) | Python 3.x stdlib | Write pretty-printed JSON report | No dependency; `json.dump(indent=2)` is the correct and sufficient tool |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | Locating `schemas/alto-2-1.xsd` relative to `pipeline.py` | Always — consistent with existing codebase pattern |
| datetime | stdlib | Timestamped report filename | Already used for `errors_TIMESTAMP.jsonl` in Phase 2 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| lxml XMLSchema | xmlschema (PyPI) | xmlschema gives richer error messages and supports all XSD 1.0/1.1 features, but adds a new dependency; lxml is already in requirements.txt and is sufficient |
| lxml XMLSchema | saxonche (Saxon/C Python) | Full XSD 1.1 support but requires paid license for advanced features and is heavy; overkill |

**Installation:** No new dependencies needed. All libraries are already in `requirements.txt` or Python stdlib.

---

## Architecture Patterns

### Recommended Project Structure
```
pipeline.py             # All logic (single-file convention — existing)
schemas/
└── alto-2-1.xsd        # Namespace-adapted copy of official ALTO 2.1 XSD (new)
output_dir/
├── alto/
│   └── *.xml           # ALTO 2.1 output (existing)
├── errors_TIMESTAMP.jsonl  # OCR error log (existing, Phase 2)
└── report_TIMESTAMP.json   # Validation+summary report (new, Phase 3)
```

### Pattern 1: XSD Startup Validation (Fail Fast)

**What:** Load the XSD file once at startup (in `main()`, before `validate_tesseract()` or pool creation), cache the `etree.XMLSchema` object, and pass it into the validation pass. If the XSD file is missing or malformed, exit immediately with a clear message.

**When to use:** Any time validation is enabled (i.e., `--validate-only` or after normal batch).

```python
# Source: https://lxml.de/validation.html
def load_xsd(schema_path: Path) -> 'etree.XMLSchema | None':
    """Load and compile the ALTO 2.1 XSD.

    Returns the compiled XMLSchema, or None if the file is missing
    (caller should warn and skip validation, not abort).

    Raises SystemExit if the file exists but is corrupt/invalid XSD.
    """
    if not schema_path.exists():
        return None
    try:
        schema_doc = etree.parse(str(schema_path))
        return etree.XMLSchema(schema_doc)
    except etree.XMLSchemaParseError as e:
        print(
            f"ERROR: ALTO XSD is corrupt or invalid: {schema_path}\n  {e}",
            file=sys.stderr,
        )
        sys.exit(1)
```

Startup check in `main()`:
```python
SCHEMA_PATH = Path(__file__).parent / 'schemas' / 'alto-2-1.xsd'
xsd = load_xsd(SCHEMA_PATH)
if xsd is None:
    print(f"WARNING: {SCHEMA_PATH} not found — XSD validation will be skipped", file=sys.stderr)
```

### Pattern 2: Per-File ALTO Validation

**What:** Parse the ALTO file, run schema validation, capture the first error from `error_log.last_error`, then walk all `String` elements to check bounding boxes against `Page` dimensions.

**When to use:** In the post-OCR validation pass, once per output ALTO file.

```python
# Source: https://lxml.de/validation.html — XMLSchema.validate() + error_log
def validate_alto_file(
    alto_path: Path,
    xsd: 'etree.XMLSchema | None',
) -> tuple[bool, str | None, list[str]]:
    """Validate an ALTO XML file against the XSD and check coordinate bounds.

    Returns:
        schema_valid: True if XSD validation passed (or XSD not available)
        schema_error: First XSD error message string, or None
        coord_violations: List of violation description strings (may be empty)
    """
    try:
        tree = etree.parse(str(alto_path))
    except etree.XMLSyntaxError as e:
        return False, f"XML parse error: {e}", []

    root = tree.getroot()

    # --- XSD validation ---
    schema_valid = True
    schema_error = None
    if xsd is not None:
        if not xsd.validate(tree):
            schema_valid = False
            err = xsd.error_log.last_error
            # err.message contains the human-readable description
            schema_error = err.message if err else "Unknown schema error"

    # --- Coordinate validation ---
    coord_violations = _check_coordinates(root)

    return schema_valid, schema_error, coord_violations


def _check_coordinates(root: etree._Element) -> list[str]:
    """Check that all word bounding boxes fall within declared page dimensions.

    Uses the ALTO 2.1 CCS-GmbH namespace.
    Returns a list of violation description strings (empty if all boxes are valid).
    """
    ns = 'http://schema.ccs-gmbh.com/ALTO'
    violations = []

    # Find the Page element for declared dimensions
    page = root.find(f'.//{{{ns}}}Page')
    if page is None:
        # No Page element — skip coordinate check (can't determine bounds)
        return []

    try:
        page_w = int(page.get('WIDTH', 0))
        page_h = int(page.get('HEIGHT', 0))
    except (ValueError, TypeError):
        return []  # Malformed dimensions — skip rather than false-positive

    if page_w == 0 or page_h == 0:
        # Missing or zero dimensions — skip coordinate check with a note
        return ['Page WIDTH or HEIGHT is 0 or missing — coordinate check skipped']

    # Check every String element
    for elem in root.iter(f'{{{ns}}}String'):
        try:
            hpos = int(elem.get('HPOS', 0))
            vpos = int(elem.get('VPOS', 0))
            width = int(elem.get('WIDTH', 0))
            height = int(elem.get('HEIGHT', 0))
        except (ValueError, TypeError):
            continue

        content = elem.get('CONTENT', '')[:40]  # Truncate for readability

        if hpos + width > page_w:
            violations.append(
                f"HPOS+WIDTH={hpos+width} > page_width={page_w} at String '{content}'"
            )
        if vpos + height > page_h:
            violations.append(
                f"VPOS+HEIGHT={vpos+height} > page_height={page_h} at String '{content}'"
            )

    return violations
```

### Pattern 3: Post-Batch Validation Pass

**What:** A `validate_batch()` function that iterates over the processed ALTO files, calls `validate_alto_file()` for each, and accumulates results into a list of per-file records. Called after `run_batch()` returns.

**When to use:** Normal mode (after OCR) and `--validate-only` mode.

```python
def validate_batch(
    file_records: list[dict],
    xsd: 'etree.XMLSchema | None',
) -> tuple[list[dict], int]:
    """Run validation pass over all processed file records.

    Args:
        file_records: List of per-file dicts already containing
                      input_path, output_path, duration_seconds,
                      word_count, error_status
        xsd: Compiled XMLSchema object, or None if XSD unavailable

    Returns:
        (updated_records, validation_warning_count)
    """
    warning_count = 0
    for record in file_records:
        # Only validate files that have ALTO output
        if record.get('error_status') != 'ok':
            record['schema_valid'] = None
            record['coord_violations'] = []
            continue

        alto_path = Path(record['output_path'])
        if not alto_path.exists():
            record['schema_valid'] = None
            record['coord_violations'] = []
            continue

        schema_valid, schema_error, coord_violations = validate_alto_file(alto_path, xsd)
        record['schema_valid'] = schema_valid
        record['schema_error'] = schema_error  # None when valid
        record['coord_violations'] = coord_violations

        has_warnings = (not schema_valid) or bool(coord_violations)
        if has_warnings:
            record['error_status'] = 'ocr_ok, validation_warnings'
            warning_count += 1

    return file_records, warning_count
```

### Pattern 4: JSON Report Writer

**What:** Assemble the run-level summary and per-file records into one dict and write with `json.dump(indent=2)`.

```python
# Source: Python stdlib json documentation
def write_report(
    output_dir: Path,
    file_records: list[dict],
    total_files: int,
    skipped: int,
    failed_ocr: int,
    validation_warnings: int,
    total_duration: float,
) -> Path:
    """Write the per-run JSON summary report.

    File is written only if at least one file was processed or validated.
    Returns the report path.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'report_{timestamp}.json'

    report = {
        'summary': {
            'total_files': total_files,
            'processed': total_files - skipped - failed_ocr,
            'skipped': skipped,
            'failed_ocr': failed_ocr,
            'validation_warnings': validation_warnings,
            'total_duration_seconds': round(total_duration, 2),
        },
        'files': file_records,
    }

    with report_path.open('w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report_path
```

### Pattern 5: `--validate-only` Mode

**What:** When `--validate-only` is passed, skip `run_batch()` and instead discover existing ALTO output files, build skeleton file_records from them (loading duration/word_count from existing data or defaults), and run `validate_batch()` + `write_report()`.

**When to use:** Re-validation after manual ALTO edits or schema updates.

```python
# In main(), after argument parsing:
if args.validate_only:
    alto_dir = args.output / 'alto'
    alto_files = sorted(alto_dir.glob('*.xml')) if alto_dir.exists() else []
    if not alto_files:
        print("No ALTO files found to validate.", file=sys.stderr)
        sys.exit(0)
    # Build skeleton records — duration/word_count unknown in validate-only mode
    file_records = [
        {
            'input_path': None,
            'output_path': str(p),
            'duration_seconds': None,
            'word_count': None,
            'error_status': 'ok',
        }
        for p in alto_files
    ]
    file_records, warning_count = validate_batch(file_records, xsd)
    # ... write report
    sys.exit(0)
```

### Anti-Patterns to Avoid

- **Re-loading the XSD inside the per-file loop:** `etree.parse()` + `etree.XMLSchema()` is expensive. Load once, reuse. The lxml `XMLSchema` object is thread-safe for read (validate) calls.
- **Using `assertValid()` instead of `validate()`:** `assertValid()` raises an exception rather than returning False; that forces try/except boilerplate and loses the clean `error_log.last_error` access pattern. Use `validate()` + check `error_log` instead.
- **Checking `len(error_log)` to detect first error:** Use `error_log.last_error` directly — it returns the most recent (and when there's only one, the first) error object. The `last_error` attribute is `None` if validation passed.
- **Using `etree.fromstring()` for validation:** `XMLSchema.validate()` requires an `_ElementTree` (from `etree.parse()`), not a bare `_Element` (from `etree.fromstring()`). Always parse from file with `etree.parse()` for the validation pass.
- **Validating against the official XSD without namespace adaptation:** The official `alto-2-1.xsd` uses `targetNamespace="http://www.loc.gov/standards/alto/ns-v2#"`. This project's output uses `http://schema.ccs-gmbh.com/ALTO`. Validating without adaptation will produce a namespace mismatch error on every file. The bundled XSD must have its namespace adapted.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| XSD parsing and validation | Custom XSD parser | `lxml.etree.XMLSchema` | lxml wraps libxml2's full XSD 1.0 implementation; hand-rolling would miss dozens of XSD constructs |
| Error message extraction | Walk `error_log` list manually | `error_log.last_error.message` | The `last_error` property gives the first error directly; no iteration needed |
| JSON pretty-printing | Custom serializer | `json.dump(indent=2)` | stdlib handles all Python primitives, None, lists, dicts; no custom encoder needed for this data shape |
| Timestamp generation | Custom time formatting | `datetime.now().strftime('%Y%m%d_%H%M%S')` | Already used for the error log in Phase 2; keep consistent |

**Key insight:** Every problem in this phase has a one-liner stdlib or already-imported-library solution. The entire implementation is orchestration glue, not new algorithm work.

---

## Common Pitfalls

### Pitfall 1: Namespace Mismatch Between Official XSD and Project Output

**What goes wrong:** Developer downloads `alto-2-1.xsd` from `github.com/altoxml/schema` and bundles it as-is. Every ALTO file the pipeline produces fails validation with a message like `Element 'alto', attribute 'xmlns': The namespace ... is not allowed.` or a targetNamespace mismatch error. 100% false-negative rate.

**Why it happens:** The official XSD uses `targetNamespace="http://www.loc.gov/standards/alto/ns-v2#"` (LoC namespace). This project intentionally uses `http://schema.ccs-gmbh.com/ALTO` (the legacy CCS-GmbH namespace required by Goobi/Kitodo). lxml XSD validation checks namespace identity strictly.

**How to avoid:** The bundled `schemas/alto-2-1.xsd` must have every occurrence of `http://www.loc.gov/standards/alto/ns-v2#` replaced with `http://schema.ccs-gmbh.com/ALTO`. This is a single string-replace on the official XSD — the element/attribute declarations are identical between the two namespace variants. A comment at the top of the file should document this adaptation.

**Warning signs:** All files report `schema_valid: false` with namespace-related error messages; no files ever pass validation even for obviously well-formed output.

### Pitfall 2: Passing `_Element` to `XMLSchema.validate()` Instead of `_ElementTree`

**What goes wrong:** Code uses `etree.fromstring(alto_path.read_bytes())` to parse the file, then passes the result to `xsd.validate()`. lxml raises a `TypeError` or silently returns `True` (behaviour depends on version).

**Why it happens:** `etree.fromstring()` returns an `_Element`; `etree.parse()` returns an `_ElementTree`. The `validate()` method requires an `_ElementTree`.

**How to avoid:** Always use `etree.parse(str(alto_path))` for the validation pass, not `etree.fromstring()`.

**Warning signs:** `TypeError: Argument 'etree' has incorrect type (expected lxml.etree._ElementTree, got lxml.etree._Element)` at runtime.

### Pitfall 3: XSD Object Re-creation Inside the File Loop

**What goes wrong:** `etree.XMLSchema(etree.parse(schema_path))` is called once per ALTO file inside the validation loop. On a 500-file batch this adds several seconds of pure overhead and unnecessary I/O.

**Why it happens:** Forgetting that the compiled `XMLSchema` object is reusable and stateless between `validate()` calls (lxml >= 3.3.2 clears the error_log correctly).

**How to avoid:** Load the XSD once at startup, before the batch loop, and pass the `etree.XMLSchema` instance into `validate_batch()`.

**Warning signs:** Profiler shows XSD parse/compile dominating the validation pass wall time.

### Pitfall 4: Report Written for Pure-Skip Runs

**What goes wrong:** A report file `report_YYYYMMDD_HHMMSS.json` is created with an empty `files` array and all-zero summary counts when the batch finds all TIFFs already processed and skips all of them.

**Why it happens:** Report-writing logic not guarded by `processed + validated > 0`.

**How to avoid:** Only call `write_report()` if `len(file_records) > 0` (i.e., at least one file was processed or validated). Document this gate in the function docstring.

**Warning signs:** Output directory fills up with zero-content report files on repeated no-op reruns.

### Pitfall 5: Coordinate Check on Files with Missing Page Dimensions

**What goes wrong:** `Page` element exists but `WIDTH` and/or `HEIGHT` are `0`, absent, or non-integer. Code computes `hpos + width > 0` which is true for essentially every word, producing thousands of false violations.

**Why it happens:** Some ALTO generators omit Page dimensions; Tesseract-produced ALTO may set them to 0.

**How to avoid:** If `page_w == 0 or page_h == 0`, append a single note string to `coord_violations` (`'Page WIDTH or HEIGHT is 0 or missing — coordinate check skipped'`) and return early. Do not iterate String elements.

**Warning signs:** Every file in the batch reports dozens of coordinate violations; all violations reference `page_width=0`.

---

## Code Examples

Verified patterns from official sources:

### Loading XSD and Validating (lxml official pattern)
```python
# Source: https://lxml.de/validation.html
from lxml import etree
from pathlib import Path

schema_doc = etree.parse(str(Path('schemas/alto-2-1.xsd')))
xsd = etree.XMLSchema(schema_doc)

tree = etree.parse(str(Path('output/alto/scan_001.xml')))
if xsd.validate(tree):
    print("Valid")
else:
    err = xsd.error_log.last_error
    print(f"Invalid: {err.message} (line {err.line})")
```

### Iterating ALTO Elements with CCS-GmbH Namespace
```python
# Source: ALTO 2.1 element model; namespace confirmed from project CLAUDE.md
NS = 'http://schema.ccs-gmbh.com/ALTO'

root = etree.parse('output/alto/scan_001.xml').getroot()
page = root.find(f'.//{{{NS}}}Page')
page_w = int(page.get('WIDTH', 0))
page_h = int(page.get('HEIGHT', 0))

for string_elem in root.iter(f'{{{NS}}}String'):
    hpos = int(string_elem.get('HPOS', 0))
    vpos = int(string_elem.get('VPOS', 0))
    w    = int(string_elem.get('WIDTH', 0))
    h    = int(string_elem.get('HEIGHT', 0))
```

### Writing Pretty-Printed JSON Report
```python
# Source: Python stdlib — https://docs.python.org/3/library/json.html
import json
from datetime import datetime
from pathlib import Path

report_path = Path('output') / f'report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
with report_path.open('w', encoding='utf-8') as f:
    json.dump(report_dict, f, indent=2, ensure_ascii=False)
```

### Namespace Adaptation Comment for Bundled XSD
```xml
<!-- schemas/alto-2-1.xsd
     ADAPTED from the official ALTO 2.1 schema (altoxml/schema v2/alto-2-1.xsd).
     targetNamespace changed from http://www.loc.gov/standards/alto/ns-v2#
     to http://schema.ccs-gmbh.com/ALTO to match this project's output namespace
     (required by Goobi/Kitodo ingest). All element/attribute declarations are
     unchanged from the official schema. -->
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| xmllint CLI for XSD validation | lxml `etree.XMLSchema` in-process | Python ecosystem ~2010 | No subprocess, error details available as Python objects |
| Manual error_log accumulation workaround | Direct `error_log.last_error` after `validate()` | lxml 3.3.2 (2014) | Error log cleared automatically between calls; no workaround needed |
| Separate violation log files | All violations in JSON report only | Project decision | Single output artifact for operator review |

**Deprecated/outdated:**
- `xmlschema.assert_()` / `assertValid()`: These are valid but force exception handling instead of the cleaner `validate()` + `error_log` pattern. Do not use for batch processing.
- lxml < 3.3.2 error_log workaround (manually tracking error counts before/after): Not needed with `lxml>=5.3.0`.

---

## Open Questions

1. **Does Goobi/Kitodo enforce XSD validation on ingest, or does it accept any well-formed XML with the correct namespace?**
   - What we know: The project deliberately uses `http://schema.ccs-gmbh.com/ALTO` because Goobi requires it (per CLAUDE.md and STATE.md).
   - What's unclear: Whether the target Goobi instance validates against the XSD on its side or only checks namespace and element names.
   - Recommendation: Proceed with XSD validation using the namespace-adapted bundled XSD. This is more rigorous than what Goobi may require, but it ensures operator confidence before ingest, which is the stated goal of this phase.

2. **Do the Tesseract-produced ALTO files include non-zero `Page WIDTH` and `HEIGHT` attributes?**
   - What we know: `build_alto21()` rewrites the namespace and applies coordinate offsets, but does not explicitly set or modify `Page WIDTH`/`HEIGHT` attributes. Tesseract's ALTO output does declare Page dimensions; after the crop offset the HPOS/VPOS coordinates of String elements are relative to the original image but Page dimensions reflect the cropped dimensions.
   - What's unclear: Whether `Page WIDTH`/`HEIGHT` in Tesseract's output reflects the cropped image or the original image dimensions after crop offset is applied.
   - Recommendation: In the coordinate check, treat `page_w == 0 or page_h == 0` as a skip condition (with a note in `coord_violations`) rather than a hard error. This is explicitly covered by the discretion decision in CONTEXT.md.

---

## Sources

### Primary (HIGH confidence)
- `https://lxml.de/validation.html` — `etree.XMLSchema` API, `validate()`, `error_log.last_error`, code examples
- `https://raw.githubusercontent.com/altoxml/schema/master/v2/alto-2-1.xsd` — Confirmed `targetNamespace="http://www.loc.gov/standards/alto/ns-v2#"` (official XSD namespace)
- `https://docs.python.org/3/library/json.html` — `json.dump()` with `indent=2`, `ensure_ascii`
- `https://bugs.launchpad.net/lxml/+bug/1222132` — Confirmed error_log accumulation fixed in lxml 3.3.2

### Secondary (MEDIUM confidence)
- `CLAUDE.md` (project file) — Confirmed `http://schema.ccs-gmbh.com/ALTO` namespace required for Goobi/Kitodo; confirmed `pipeline.py` single-file architecture
- `STATE.md` (project file) — Confirmed lxml already in stack; confirmed `ALTO21_NS = 'http://schema.ccs-gmbh.com/ALTO'`
- Wikipedia / COPTR ALTO article (via search) — Confirmed CCS GmbH developed ALTO 1.0–1.4 (2004–2007); LoC took over in 2009; explains the namespace split

### Tertiary (LOW confidence)
- None — all claims verified against official sources or project files.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — lxml already in requirements.txt; confirmed via official lxml docs
- Architecture: HIGH — patterns derived directly from lxml official API docs and project's existing conventions (single-file, same timestamp pattern as error log)
- Pitfalls: HIGH — namespace mismatch verified by fetching the actual XSD; lxml API pitfalls verified via official docs and bug tracker

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (lxml stable; ALTO 2.1 XSD is frozen; Python stdlib json is stable)
