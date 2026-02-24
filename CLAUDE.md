# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Batch OCR pipeline: archival journal/magazine TIFFs → ALTO 2.1 XML for ingest into Goobi/Kitodo (DFG Viewer). Phase 1 (single-file) and Phase 2 (batch/parallel) are complete. Phase 3 adds XSD validation and reporting.

## System Dependencies

```bash
# macOS
brew install tesseract tesseract-lang

# Linux
apt install tesseract-ocr tesseract-ocr-deu
```

## Setup and Run

```bash
pip install -r requirements.txt

# Process a folder of TIFFs (batch mode — Phase 2+)
python pipeline.py --input ./scans/ --output ./output

# Key flags
--lang deu          # Tesseract language (default: deu)
--psm 1             # Page segmentation mode (default: 1 = auto with OSD)
--padding 50        # Crop border padding in pixels (default: 50)
--workers N         # Parallel workers (default: min(cpu_count, 4))
--force             # Reprocess TIFFs that already have ALTO XML output
```

Output: `<output_dir>/alto/<stem>.xml` per TIFF
Error log (if failures): `<output_dir>/errors_YYYYMMDD_HHMMSS.jsonl`

Stdout on success: `Done: N processed, M skipped, 0 failed`
Per-file line (from worker): `scan_001.tif → output/alto/scan_001.xml (11.1s, 46 words)`
Warnings appear inline: `... [WARN: no DPI tag, using 300]`
Errors go to stderr with exit code 1.

## Architecture

`pipeline.py` is a single-file script with functions in dependency order:

```
load_tiff()           → (PIL Image, dpi tuple, warnings list)
detect_crop_box()     → (crop box, fallback_used bool)
run_ocr()             → ALTO XML bytes (Tesseract native, ALTO 3.x namespace)
build_alto21()        → ALTO XML bytes (ALTO 2.1 namespace, crop offset applied)
count_words()         → int
process_tiff()        → writes output file, prints result line  [raises on error]
validate_tesseract()  → None (exits with message if Tesseract absent or lang missing)
discover_tiffs()      → sorted list of Path objects
write_error_log()     → Path | None (writes JSONL, returns None if no errors)
run_batch()           → (processed, skipped, error_list)
main()                → argparse wiring
```

### Three correctness invariants in `build_alto21()`

All three must remain in order:

1. **xsi:schemaLocation stripped first** — `root.attrib.pop('{...}schemaLocation', None)` at Step 2, before serialization. Must happen before the namespace rewrite.

2. **Crop offset before namespace rewrite** — HPOS/VPOS offsets are applied using the ALTO 3.x namespace tag names. After the namespace string-replace the tag names change, so the offset must happen first (Step 2 before Step 4).

3. **WIDTH/HEIGHT are never modified** — only HPOS and VPOS receive the crop offset. Modifying dimensions would break the ALTO layout model.

### Correct namespace

Tesseract emits `http://www.loc.gov/standards/alto/ns-v3#`. This must be rewritten to `http://schema.ccs-gmbh.com/ALTO` (CCS-GmbH ALTO 2.1) for Goobi/Kitodo ingest.

### Crop detection

Uses `cv2.THRESH_BINARY + cv2.THRESH_OTSU` (NOT `THRESH_BINARY_INV`). For archival scans (dark scanner bed, light page), THRESH_BINARY makes the page content the dominant white region so `findContours` returns the page as the largest contour. The inverse would detect the scanner bed instead.

Fallback to original bounds if detected area is outside 40–98% of total image area.

### Batch error isolation

`process_tiff()` must `raise` (not `sys.exit`) on error — required for `ProcessPoolExecutor` workers on macOS/spawn. `run_batch()` uses `submit()` + `as_completed()` (not `executor.map()`) to collect per-file exceptions without aborting the batch.

## Roadmap State

- **Phase 3 (next):** ALTO 2.1 XSD validation per file, coordinate sanity checks, JSON summary report per run.

See `.planning/ROADMAP.md` for full requirements.
