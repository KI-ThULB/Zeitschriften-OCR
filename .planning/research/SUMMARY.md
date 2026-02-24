# Project Research Summary

**Project:** Zeitschriften-OCR — TIFF Batch OCR to ALTO XML Pipeline
**Domain:** Digital library document processing / archival OCR tooling
**Researched:** 2026-02-24
**Confidence:** HIGH

## Executive Summary

This project is a batch OCR pipeline for digitized archival journal scans: TIFF input, ALTO 2.1 XML output, designed for ingest into Goobi/Kitodo digital library workflows. The domain is well-understood — Tesseract 5.x with LSTM engine is the established choice for German archival text, pytesseract provides the Python binding with direct ALTO output, and OpenCV handles scan border detection. The stack is deliberately minimal: five pip packages plus a system-level Tesseract install. No web framework, no database, no message queue — this is a local CLI batch tool and must stay that way.

The recommended build order follows clear dependency constraints: the single-file pipeline (load → crop → OCR → ALTO) must be correct before parallelism is introduced, and parallelism must be stable before robustness hardening is worth doing. The most important correctness concerns are DPI preservation (controls coordinate accuracy in Goobi), ALTO namespace correction (Tesseract emits ALTO 3.x; Goobi requires 2.1), and crop-to-original coordinate offset (Tesseract coordinates are relative to the cropped image, but Goobi displays the original TIFF — offset correction is mandatory).

The main risk is silent incorrectness: ALTO files that are structurally valid XML but have wrong coordinates or wrong namespace will pass file-system checks, be accepted by ingest pipelines, and only fail visibly when an operator tries to view fulltext highlights in the DFG Viewer. All three of the top pitfalls (DPI errors, namespace mismatch, coordinate offset) produce this failure mode. The mitigation strategy is to build schema validation and coordinate sanity checks into the pipeline from the start, not as a later addition.

## Key Findings

### Recommended Stack

The stack is lean and high-confidence across all components. Pillow handles large TIFF I/O with lazy loading — critical for 117–240 MB files. OpenCV (headless) handles border detection via contour analysis. pytesseract wraps Tesseract 5.x for both OCR and native ALTO output. lxml handles namespace correction and XSD validation. ProcessPoolExecutor (stdlib) provides process-based parallelism that bypasses Python's GIL for CPU-bound OCR work. tqdm provides thread-safe progress reporting. No component in this stack is controversial or experimental.

See `/Users/zu54tav/Zeitschriften-OCR/.planning/research/STACK.md` for full details and version constraints.

**Core technologies:**
- **Pillow >= 10.x**: TIFF I/O with lazy loading — preserves DPI metadata, avoids immediate RAM spike
- **opencv-python-headless >= 4.9.x**: Border/margin detection — headless variant correct for server/batch use
- **pytesseract >= 0.3.13 + Tesseract 5.3.x**: OCR and ALTO XML output — LSTM engine required for German
- **lxml >= 5.0.0**: ALTO namespace correction and XSD schema validation
- **concurrent.futures.ProcessPoolExecutor**: Parallel batch processing — process-based for GIL bypass
- **tqdm >= 4.66.x**: Progress reporting — thread-safe with concurrent.futures
- **argparse (stdlib)**: CLI interface — no extra dependency needed

**Critical version note:** Tesseract must be 5.x (LSTM). Tesseract 4.x accuracy for German is significantly worse.

### Expected Features

See `/Users/zu54tav/Zeitschriften-OCR/.planning/research/FEATURES.md` for full feature list with complexity ratings.

**Must have (table stakes):**
- Batch processing of all TIFFs in a folder with skip-already-processed logic
- Border/margin detection and crop before OCR (coordinates change post-crop — this is a hard ordering constraint)
- DPI extraction from TIFF metadata and passthrough to Tesseract
- ALTO 2.1 XML output, one file per TIFF, schema-valid with correct namespace
- Word-level bounding boxes with crop offset correction applied
- Per-file error isolation — one broken TIFF must not abort the batch
- Error log file recording failures with stack traces
- CLI: `--input`, `--output`, `--workers`, `--lang`, `--padding`, `--force`

**Should have (differentiators):**
- Summary report (JSON/CSV) with per-file timing, word count, and error status
- ALTO schema validation per output file with logged failures (non-aborting)
- Coordinate sanity check (all word boxes within page dimensions)
- Dry run mode (`--dry-run`)
- Verbose logging (`--verbose`)
- Deskew detection for rotated scans
- Adaptive thresholding for uneven illumination

**Defer to v2+:**
- GUI or web interface
- ALTO 3.x / 4.x output variants
- Database tracking of processed files
- Multi-language OCR per run
- PDF input
- Image quality scoring
- Goobi/Kitodo plugin packaging
- Cloud/distributed processing

### Architecture Approach

The architecture is a sequential pipeline per file, parallelized at the file level via ProcessPoolExecutor. Each worker subprocess runs the full 6-step pipeline independently: ImageLoader → CropDetector → Cropper → OCRRunner → ALTOBuilder → ALTOWriter. The main process only orchestrates dispatch, collects results, and handles progress reporting. Memory isolation between workers means one malformed TIFF cannot affect other workers. Skip logic is disk-based (file existence check), making batch reruns safe without any database or state file.

See `/Users/zu54tav/Zeitschriften-OCR/.planning/research/ARCHITECTURE.md` for component interfaces, data flow diagram, and memory sizing guidance.

**Major components:**
1. **CLI Entry Point** — argument parsing, path validation, file list resolution, worker count configuration
2. **Batch Orchestrator** — ProcessPoolExecutor dispatch, result collection, progress bar, error log aggregation
3. **ImageLoader** — Pillow lazy open, DPI extraction with 300 DPI fallback and warning
4. **CropDetector** — OpenCV grayscale/threshold/contour pipeline, fallback to original bounds if detection implausible
5. **OCRRunner** — pytesseract call with DPI and PSM passthrough, returns raw ALTO XML string
6. **ALTOBuilder** — lxml namespace rewrite to ALTO 2.1, crop offset injection into coordinates, XSD validation
7. **ALTOWriter** — atomic write (`.xml.tmp` then rename) to prevent corrupt half-written files

**Key architectural constraints:**
- ProcessPoolExecutor (not ThreadPoolExecutor) — CPU-bound work, GIL is a real bottleneck with threads
- Conservative default worker count: `min(os.cpu_count(), 4)` — 240 MB TIFFs expand to 500–800 MB RAM each
- Output written atomically to prevent corruption on crash/OOM
- Output directory created at startup (not in workers) to avoid race conditions

### Critical Pitfalls

See `/Users/zu54tav/Zeitschriften-OCR/.planning/research/PITFALLS.md` for full risk analysis with detection signs.

1. **Wrong DPI in ALTO coordinates** (HIGH risk) — TIFF missing DPI tag causes Tesseract to default to 70 DPI, producing grossly wrong coordinates that display incorrectly in Goobi. Prevention: always extract DPI from TIFF metadata; default to 300 (not 70/72/96) with an explicit warning log; pass `--dpi N` to Tesseract explicitly.

2. **ALTO namespace mismatch** (HIGH risk) — Tesseract/pytesseract emit ALTO 3.x namespace by default; Goobi requires ALTO 2.1 (`xmlns="http://schema.ccs-gmbh.com/ALTO"`). Files pass file-system checks but fail ingest. Prevention: lxml namespace rewrite is mandatory in ALTOBuilder; validate against ALTO 2.1 XSD during development.

3. **Crop coordinate offset not applied** (HIGH risk, subtle) — Tesseract reports coordinates relative to the cropped image, but if Goobi displays the original TIFF, all word highlights will be offset by exactly the crop margin. Prevention: ALTOBuilder must add `crop_x` to HPOS and `crop_y` to VPOS before writing.

4. **Memory exhaustion from large TIFFs** (HIGH risk at scale) — OpenCV `cv2.imread()` loads full decompressed pixel array immediately; 4 workers with 240 MB TIFFs = 3+ GB RAM. Prevention: use Pillow lazy open; discard numpy array immediately after crop detection; tune worker count to available RAM.

5. **Crop detection failure on edge cases** (MEDIUM risk) — contour detection fails on light-border scans or pages with color calibration charts, producing crop boxes that are either too aggressive or miss the border entirely. Prevention: fallback to original bounds if `detected_area / original_area < 0.4` or `> 0.98`; log fallback triggers; test on 10–20 representative samples before full batch.

## Implications for Roadmap

Research identifies three natural phases with hard dependency ordering. The architecture research explicitly calls out this build order; it is not a preference but a correctness constraint.

### Phase 1: Single-File Pipeline (Core Correctness)

**Rationale:** All downstream phases depend on correct per-file output. The three highest-risk pitfalls (DPI, namespace, coordinate offset) are all Phase 1 problems. Parallelism and batch hardening are pointless if the single-file output is wrong. This must be validated on real sample files before Phase 2 begins.

**Delivers:** A working CLI that processes one TIFF to a schema-valid ALTO 2.1 file with correct coordinates.

**Addresses features:** Image loading with DPI extraction, border detection, OCR with language/PSM config, ALTO 2.1 output with namespace correction, coordinate offset correction.

**Avoids pitfalls:** DPI error, namespace mismatch, crop offset, memory (via Pillow lazy load).

**Research flag:** Standard patterns, well-documented. No additional research needed — all interfaces and algorithms are specified in STACK.md and ARCHITECTURE.md.

### Phase 2: Batch Orchestration and CLI

**Rationale:** Depends on Phase 1 being correct for a single file. Adds ProcessPoolExecutor dispatch, skip logic, error isolation, progress reporting, and the full CLI surface. Memory management (worker count defaults) and atomic output writes belong here.

**Delivers:** A production-usable CLI that processes a full folder of TIFFs in parallel, skips already-processed files, logs errors, and reports progress.

**Addresses features:** `--input`, `--output`, `--workers`, `--force`, `--lang`, `--padding`, batch skip logic, per-file error isolation, error log file, progress bar.

**Avoids pitfalls:** Worker crashes losing progress (atomic writes + disk-based skip logic), memory exhaustion (conservative worker defaults), Tesseract language pack missing (startup validation).

**Research flag:** Standard patterns. ProcessPoolExecutor with futures is well-documented. No additional research needed.

### Phase 3: Robustness and Reporting

**Rationale:** Depends on Phase 2 for realistic error scenarios and edge cases. Adds validation, reporting, operational aids, and handles edge cases discovered during Phase 2 testing on the full batch.

**Delivers:** Validated output with per-file reports, ALTO schema validation results, coordinate sanity checks, dry run mode, verbose logging, and (if needed) deskew and adaptive thresholding.

**Addresses features:** Summary report (JSON/CSV), ALTO XSD validation per file, coordinate sanity check, `--dry-run`, `--verbose`, crop detection fallback hardening, deskew detection (if scans show rotation).

**Avoids pitfalls:** Crop detection edge cases (fallback logic + logging), silent ALTO invalidity (schema validation integrated into pipeline).

**Research flag:** Deskew detection may benefit from a focused research spike if scan quality is variable. OpenCV deskew patterns are documented but calibration depends on actual scan characteristics.

### Phase Ordering Rationale

- Phase 1 before Phase 2: the 6-step pipeline produces all data that the orchestrator will parallelize. Running Phase 2 on a broken pipeline just scales up incorrect output.
- Phase 2 before Phase 3: realistic error scenarios (crop failure, corrupt TIFFs, OOM) only emerge at batch scale. Building robustness handlers before seeing real failures adds speculative complexity.
- DPI + namespace + offset pitfalls are all Phase 1: they are single-file correctness issues, not scaling issues. Fixing them early prevents incorrect ALTO files from accumulating in output directories.
- Atomic writes belong in Phase 2: they protect against partial batches, not single-file runs.

### Research Flags

Phases needing deeper research during planning:
- **Phase 3 (deskew):** If scan rotation is common in the Zeitschriften collection, deskew detection needs a calibration pass on representative samples. OpenCV Hough transform or scikit-image `determine_skew` patterns are available but require tuning.

Phases with standard patterns (skip additional research):
- **Phase 1:** All algorithms (Pillow lazy load, OpenCV contour crop, pytesseract ALTO, lxml namespace rewrite) are specified with working code patterns in research files.
- **Phase 2:** ProcessPoolExecutor with futures is stdlib and well-documented. Skip logic pattern is explicit in ARCHITECTURE.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries are well-established; versions pinned to current stable releases; explicit "do not use" list based on known failure modes |
| Features | HIGH | Derived from digital library production requirements (Goobi/Kitodo context); anti-features are clearly justified |
| Architecture | HIGH | Component boundaries are explicit with typed interfaces; parallelism model is specific (ProcessPoolExecutor, not ThreadPoolExecutor); memory math is provided |
| Pitfalls | HIGH | All pitfalls include warning signs, root causes, prevention steps, and phase assignment; the coordinate offset pitfall is non-obvious and well-documented |

**Overall confidence:** HIGH

### Gaps to Address

- **Actual DPI values in the Zeitschriften collection:** Research assumes 300–400 DPI. If some TIFFs have no DPI tag or wildly inconsistent values (e.g., 72 DPI from a scanner misconfiguration), the default fallback value (300) may be wrong. Validate DPI metadata on a sample of 20–30 actual TIFFs before Phase 1 cutover.

- **Goobi coordinate system confirmation:** Research identifies that Goobi displays the original (uncropped) TIFF and therefore ALTO coordinates must include crop offset. This should be confirmed with the actual Goobi instance / Goobi workflow documentation before Phase 1 is considered complete.

- **Scan border characteristics:** Crop detection fallback thresholds (40%/98%) are based on typical archival scans. Validate on 10–20 representative Zeitschriften samples to check whether the thresholds need tuning before Phase 1 ships.

- **ALTO 2.1 MeasurementUnit:** Research recommends `mm10` as measurement unit (tenths of millimeters). If the target Goobi instance expects `pixel` units, the coordinate conversion formula changes entirely. Confirm with Goobi configuration or existing ALTO files from the same workflow.

## Sources

### Primary (HIGH confidence)
- pytesseract library documentation — ALTO output, DPI config, PSM flags
- lxml library documentation — ElementTree, XMLSchema validation, namespace handling
- OpenCV documentation — `findContours`, `boundingRect`, `threshold` APIs
- Pillow documentation — `Image.open()` lazy loading, TIFF DPI metadata via `image.info`
- Python stdlib documentation — `concurrent.futures.ProcessPoolExecutor`, `as_completed`
- ALTO 2.1 specification — `MeasurementUnit`, `HPOS`/`VPOS`/`WIDTH`/`HEIGHT` semantics, namespace URI

### Secondary (MEDIUM confidence)
- Archival OCR community practice — Tesseract 5.x LSTM preference for German historical text
- Digital library workflow conventions — Goobi/Kitodo ALTO ingest requirements
- Memory sizing estimates — based on TIFF decompression ratios for 400 DPI archival scans

### Tertiary (LOW confidence)
- Deskew detection patterns — OpenCV Hough / scikit-image `determine_skew`; needs calibration on actual collection samples
- Worker count defaults — `min(os.cpu_count(), 4)` is a heuristic; actual safe value depends on available RAM and TIFF sizes in this specific collection

---
*Research completed: 2026-02-24*
*Ready for roadmap: yes*
