# Phase 1: Single-File Pipeline - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Process a single TIFF file through the full pipeline: load with DPI extraction → auto-detect and crop scan borders → run Tesseract OCR → write a schema-valid ALTO 2.1 XML file with correct namespace and word coordinates offset to match the original (uncropped) TIFF. Phase 2 adds batch orchestration and the full CLI surface. Phase 3 adds validation and reporting.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- Single script: `pipeline.py` at the repo root — no package structure, no install required
- Invocation: `python pipeline.py --input <tiff> --output <dir>`
- Python 3.10+ (modern type hints, match/case available)
- Dependencies declared in `requirements.txt`

### Output File Naming
- ALTO XML filename: same stem as input TIFF, `.xml` extension — `scan_001.tif` → `scan_001.xml`
- Output placed in `<output_dir>/alto/` subfolder — e.g. `output/alto/scan_001.xml`
- `<output_dir>/alto/` is created automatically if it doesn't exist

### Logging & Feedback
- Successful run: one-line result to stdout: `scan_001.tif → output/alto/scan_001.xml (1.2s, 847 words)`
- Warnings (missing DPI tag, crop fallback triggered) appended inline to the result line: `... [WARN: no DPI tag, using 300]`
- Errors: message to stderr (`ERROR: scan_001.tif: <reason>`) and exit code 1 — no Python traceback by default

### Crop Configuration
- `--padding PX` CLI flag to set margin around detected content area (default: 50px)
- `--no-crop` flag to bypass OpenCV detection entirely and use original TIFF bounds — for already-clean scans
- Fallback thresholds (40% / 98%) hardcoded in Phase 1; not yet exposed as flags

### Claude's Discretion
- Exact contour detection parameters (Otsu threshold settings, erosion/dilation pre-processing)
- ALTO 2.1 internal structure (MeasurementUnit, Layout/Page element nesting)
- How to handle multi-page TIFFs (if any exist — treat as single-page or error)
- Temp file handling for pytesseract I/O

</decisions>

<specifics>
## Specific Ideas

- The output line format should be scriptable — key values (time, word count) are extractable by downstream tooling
- Errors to stderr means the script can be used in shell pipelines: `python pipeline.py ... && echo "ok"`
- The `--no-crop` flag is especially useful for a quick quality check: run without crop first, compare result

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within Phase 1 scope

</deferred>

---

*Phase: 01-single-file-pipeline*
*Context gathered: 2026-02-24*
