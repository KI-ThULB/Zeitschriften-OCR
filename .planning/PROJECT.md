# Zeitschriften-OCR

## What This Is

A batch processing pipeline for digitized journal and magazine scans. It takes several hundred large archival TIFF files (117–240 MB each), automatically deskews and crops each scan, runs Tesseract OCR in parallel, validates the output against the ALTO 2.1 XSD schema, and writes one ALTO 2.1 XML file per TIFF — ready for ingest into Goobi/Kitodo-based digital library systems and display in the DFG Viewer.

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

### Active

None.

### Out of Scope

- Saving cropped TIFFs as permanent deliverables — only needed as intermediate for OCR
- GUI or web interface — command-line tool only
- ALTO 3.x / 4.x output — target is ALTO 2.1 for Goobi/Kitodo compatibility
- Languages other than German — pipeline optimized for modern German text
- Direct Goobi/Kitodo plugin integration — standalone tool, ingest handled separately

## Context

- Input: several hundred TIFF files, 117–240 MB each (archival resolution, likely 400–600 DPI)
- Content type: digitized German-language journals and magazines (modern typeface)
- Scan border issue: scanner bed artifacts need algorithmic removal before OCR
- Target system: DFG Viewer / Goobi / Kitodo — requires ALTO 2.1 XML with word-level coordinates
- Platform: macOS development (must also run on Linux servers for batch production)
- Current codebase: 873 lines Python (`pipeline.py`) + `schemas/alto-2-1.xsd`; 6 pinned dependencies (added `deskew>=1.5.0`)

## Constraints

- **Format**: ALTO 2.1 XML — mandated by Goobi/Kitodo ingest pipeline
- **OCR engine**: Tesseract — open source, established in German library workflows
- **Language model**: `deu` (German) Tesseract trained data
- **Originals**: Must never be modified or overwritten
- **Output layout**: `<output_dir>/alto/<filename>.xml` alongside input folder

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Tesseract for OCR | Open source, standard in German digital library ecosystem, good `deu` model | ✓ Good — verified on real scan |
| OpenCV for crop detection | Robust contour/edge detection for scanner border removal | ✓ Good — THRESH_BINARY + THRESH_OTSU works correctly for dark-bed scans |
| THRESH_BINARY (not INV) | Archival scans have dark scanner bed, light page — THRESH_BINARY makes page content the largest white contour | ✓ Good — confirmed in 01-01 |
| ALTO21_NS = `http://schema.ccs-gmbh.com/ALTO` | CCS-GmbH namespace required by Goobi/Kitodo (not Tesseract's ALTO 3.x default) | ✓ Good — namespace verified in output |
| Crop offset BEFORE namespace rewrite | ALTO3_NS element lookup must precede string replace or tag names change | ✓ Good — critical ordering invariant in build_alto21() |
| WIDTH/HEIGHT not offset | Only HPOS/VPOS receive crop offset; modifying dimensions would break ALTO layout model | ✓ Good — verified invariant |
| opencv-python-headless | Server/batch use without display dependency | ✓ Good |
| `process_tiff()` uses `raise` not `sys.exit` | `sys.exit` in ProcessPoolExecutor workers kills parent process pool on macOS/spawn | ✓ Good — critical fix in 02-01 |
| `executor.submit()` + `as_completed()` | `executor.map()` aborts on first exception; submit/as_completed isolates per-file errors | ✓ Good — BATC-03 requirement |
| XSD bundled at `schemas/alto-2-1.xsd` | No network dependency at runtime; namespace-adapted to CCS-GmbH namespace (LoC upstream ns would fail validation) | ✓ Good — XSD compiles correctly, live smoke test passed |
| Validation as separate post-OCR pass | Clean separation from OCR parallelism; `--validate-only` re-validation possible without re-running OCR | ✓ Good — VALD-01/02/03 satisfied |
| `deskew` library (Hough-line) over projection-profile | More robust on mixed-content archival pages with illustrations and column rules | ✓ Good — clean results, plausibility gate at 10° |
| Deskew before crop (not after) | Page contour is axis-aligned when OpenCV `findContours` runs — prevents crop fallback on deskewed images | ✓ Good — critical ordering invariant |
| `DESKEW_MAX_ANGLE = 10.0` named constant | Archival periodical skew is under 5°; 10° gate catches misdetections without being too aggressive | ✓ Good — tunable if corpus changes |
| `--adaptive-threshold` opt-in (off by default) | Default pipeline behavior preserved; operator enables only for problematic scans | ✓ Good — PREP-05 requirement satisfied |
| `ADAPTIVE_BLOCK_SIZE = 51`, `ADAPTIVE_C = 10` as named constants | Starting values for corpus tuning; named constants make them adjustable without code search | ○ Pending empirical tuning against real scans |

## Known Technical Debt

- `ADAPTIVE_BLOCK_SIZE = 51` and `ADAPTIVE_C = 10` are informed starting points; empirical tuning against real Zeitschriften corpus scans is recommended before batch production with `--adaptive-threshold`.

---
*Last updated: 2026-02-25 after v1.2 milestone*
