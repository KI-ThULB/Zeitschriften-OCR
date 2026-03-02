# Zeitschriften-OCR

## What This Is

A tool for digitizing archival journal and magazine scans. It takes large TIFF files (117–240 MB each), automatically deskews and crops each scan, runs Tesseract OCR in parallel, and writes one ALTO 2.1 XML file per TIFF — ready for ingest into Goobi/Kitodo-based digital library systems. A local Flask web application wraps the pipeline with a drag-and-drop upload interface, live SSE progress, a side-by-side TIFF/text viewer with inline word correction, VLM-powered article segmentation, METS/MODS export, and full-text article search.

## Current State: v1.5 Shipped

All 18 phases complete. The full operator workflow is live:
- OCR pipeline (CLI) → ALTO 2.1 XML per TIFF
- Web UI: drag-and-drop upload, live progress, side-by-side viewer, inline word correction
- VLM article segmentation (Claude / OpenAI / OpenAI-compatible) with bounding boxes per page
- METS/MODS logical structure export (DFG Viewer / Goobi-Kitodo profile)
- Web-based VLM settings (Open WebUI / OpenRouter), persisted to settings.json
- SQLite FTS5 full-text article search with deep-link viewer navigation

## Core Value

Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.

## Requirements

### Validated

- ✓ Auto-detect and crop scan borders/margins from each TIFF (OpenCV contour detection) — v1.0
- ✓ Run Tesseract OCR on the cropped image with German language model — v1.0
- ✓ Output one ALTO 2.1 XML file per TIFF to a sibling output folder — v1.0
- ✓ CLI invocation: user specifies input file and output folder (single-file mode) — v1.0
- ✓ Process files in parallel with ProcessPoolExecutor; skip already-processed on rerun — v1.1
- ✓ Per-file error isolation; JSONL error log per run — v1.1
- ✓ Full batch CLI (`--input DIR`, `--output DIR`, `--workers`, `--force`, `--lang`, `--padding`, `--psm`) — v1.1
- ✓ Validate ALTO 2.1 output against bundled XSD schema per file — v1.1
- ✓ Per-run JSON summary report with coordinate sanity check and `--validate-only` flag — v1.1
- ✓ Detect and correct scan rotation (deskew) before OCR; angle logged per file — v1.2
- ✓ Apply opt-in adaptive Gaussian thresholding for scans with uneven illumination (`--adaptive-threshold`) — v1.2
- ✓ `--dry-run` flag lists every TIFF that would be processed and every TIFF that would be skipped, then exits without running OCR — v1.3
- ✓ `--verbose` flag prints Tesseract stdout/stderr and per-stage wall-clock timing (deskew, crop, OCR, write) for each processed file — v1.3
- ✓ Live progress line during batch: files completed / total / percentage / ETA (rolling average) — v1.3
- ✓ `--config PATH` loads CLI flag defaults from a JSON file; CLI flags always override config values — v1.3
- ✓ Missing or invalid `--config` file exits with a clear error before any TIFF is processed — v1.3
- ✓ Flask web server with background OCR worker, SSE stream, skip/error isolation — v1.4
- ✓ TIFF→JPEG endpoint with jpegcache; ALTO word array JSON endpoint — v1.4
- ✓ Browse all processed files and view TIFF + extracted OCR text side by side — v1.4
- ✓ Click a word in the text panel to highlight its bounding box on the TIFF image — v1.4
- ✓ Bounding box overlay scales correctly on window resize (ResizeObserver) — v1.4
- ✓ Prev/Next navigation with keyboard shortcuts — v1.4
- ✓ Inline word correction with atomic ALTO XML write and XSD validation gate — v1.5 (Phase 12)
- ✓ Drag-and-drop upload UI with file queue, Start button, live SSE progress bar, results links — v1.5 (Phase 13)
- ✓ Mouse-wheel zoom + click-drag pan with aligned SVG word overlay — v1.5 (Phase 14)
- ✓ VLM article segmentation via configurable provider (`--vlm-provider` / `--vlm-model` CLI flags or web settings UI) — v1.5 (Phase 15+17)
- ✓ Article regions with bounding box, type, and title stored per page in segment JSON — v1.5 (Phase 15)
- ✓ Article title and section type accessible as structured metadata via `/articles/<stem>` and FTS5 search — v1.5 (Phase 15+18)
- ✓ METS/MODS logical structure document per DFG Viewer / Goobi-Kitodo profile — v1.5 (Phase 16)
- ✓ Viewer article browser — article cards with type/title, click to highlight region on TIFF — v1.5 (Phase 18)
- ✓ Full-text search across all articles from the web interface; deep-link to `/viewer/<stem>#<region_id>` — v1.5 (Phase 18)

### Active

(none — all v1.5 requirements complete)

### Out of Scope

- Saving cropped TIFFs as permanent deliverables — only needed as intermediate for OCR
- GUI or web interface for headless server batch runs — web app targets local operator workstation use; server batch runs remain CLI-only
- ALTO 3.x / 4.x output — target is ALTO 2.1 for Goobi/Kitodo compatibility
- Languages other than German — pipeline optimized for modern German text
- Direct Goobi/Kitodo plugin integration — standalone tool, ingest handled separately
- Multi-user / authentication — local single-operator tool
- ALTO structural editing (merge/split words) — different problem class; extreme complexity

## Context

- Input: several hundred TIFF files, 117–240 MB each (archival resolution, likely 400–600 DPI)
- Content type: digitized German-language journals and magazines (modern typeface)
- Scan border issue: scanner bed artifacts need algorithmic removal before OCR
- Target system: DFG Viewer / Goobi / Kitodo — requires ALTO 2.1 XML with word-level coordinates
- Platform: macOS development (must also run on Linux servers for batch production)
- Current codebase: ~6,600 lines total — `pipeline.py`, `app.py`, `search.py`, `vlm.py`, `mets.py`, `templates/`, `tests/`; 133 tests passing
- Tech stack: Python, Flask 3.1, Tesseract, Pillow, OpenCV, lxml, SQLite FTS5, vanilla JS

## Constraints

- **Format**: ALTO 2.1 XML — mandated by Goobi/Kitodo ingest pipeline
- **OCR engine**: Tesseract — open source, established in German library workflows
- **Language model**: `deu` (German) Tesseract trained data
- **Originals**: Must never be modified or overwritten
- **Output layout**: `<output_dir>/alto/<filename>.xml` alongside input folder

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Tesseract for OCR | Open source, standard in German digital library ecosystem, good `deu` model | ✓ Good |
| OpenCV THRESH_BINARY + THRESH_OTSU | Dark-bed scans: THRESH_BINARY makes page content largest white contour | ✓ Good |
| ALTO21_NS = `http://schema.ccs-gmbh.com/ALTO` | CCS-GmbH namespace required by Goobi/Kitodo | ✓ Good |
| Crop offset BEFORE namespace rewrite | ALTO3_NS element lookup must precede string replace | ✓ Good |
| `process_tiff()` raises (not sys.exit) | sys.exit in ProcessPoolExecutor workers kills parent on macOS/spawn | ✓ Good |
| `executor.submit()` + `as_completed()` | executor.map() aborts on first exception; submit/as_completed isolates errors | ✓ Good |
| XSD bundled at `schemas/alto-2-1.xsd` | No network dependency; namespace-adapted to CCS-GmbH | ✓ Good |
| Validation as separate post-OCR pass | Clean separation; `--validate-only` works without re-running OCR | ✓ Good |
| Flask web app, local-only | Browser as UI; no Electron/Qt; no auth needed for single operator | ✓ Good |
| Vanilla JS, no bundler | Entire viewer in templates/viewer.html; no npm, no build step | ✓ Good |
| Shared container transform for zoom/pan | Single `#image-container` div wraps img + SVG — no per-word coordinate recalculation | ✓ Good |
| Atomic write via tempfile.mkstemp + os.replace | No partial-write corruption on ALTO XML edits | ✓ Good |
| threading.Thread (not ProcessPoolExecutor) for _ocr_worker | Enables per-file SSE streaming; avoids macOS spawn issues | ✓ Good |
| OpenAICompatibleProvider with lazy openai import | Single class covers Open WebUI, OpenRouter, Ollama; no SDK required at import time | ✓ Good |
| VLM settings.json in output_dir | Persists across server restarts; no separate config file needed | ✓ Good |
| SQLite FTS5 DELETE+INSERT for idempotent upsert | FTS5 INSERT OR REPLACE semantics differ from regular tables | ✓ Good |
| `stem UNINDEXED` in FTS5 schema | stem is a lookup key, not content to tokenize | ✓ Good |
| GET /articles/<stem> reads segment JSON directly | Always consistent with authoritative JSON; no DB state dependency | ✓ Good |
| `GET /search` serves HTML page; `GET /api/search` returns JSON | Avoids route conflict; clean content-type split | ✓ Good |
| article-highlight-rect uses `style.display = 'block'` (not `''`) | CSS rule sets display:none; empty string removes inline override but CSS wins | ✓ Good |

## Known Technical Debt

- `ADAPTIVE_BLOCK_SIZE = 51` and `ADAPTIVE_C = 10` are informed starting points; empirical tuning against the real Zeitschriften corpus is recommended before batch production with `--adaptive-threshold`.
- VLM reasoning models (e.g. Gemini 2.5 Pro) consume nearly all output tokens for internal reasoning, leaving insufficient tokens for JSON output — non-reasoning models (GPT-4o, Claude Sonnet) are required for structured region output.

---
*Last updated: 2026-03-02 after v1.5 milestone completion*
