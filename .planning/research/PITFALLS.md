# Pitfalls Research: TIFF Batch OCR → ALTO XML Pipeline

## Critical Pitfalls

### 1. Memory Exhaustion from Large TIFFs

**Risk:** HIGH — files are 117–240 MB. OpenCV `cv2.imread()` loads the full decompressed pixel array immediately. A 240 MB compressed TIFF can expand to 800 MB+ as a raw numpy array. With 4 parallel workers this is 3+ GB just for images.

**Warning signs:**
- Workers killed by OOM killer on Linux
- `MemoryError` in Python workers
- Machine becomes unresponsive during batch

**Prevention:**
- Use `Pillow.Image.open()` (lazy) for initial load — only decodes pixels when accessed
- Convert to numpy/OpenCV array only for crop detection, then discard the full-res array
- Pass the PIL Image (not numpy array) to Tesseract — pytesseract handles the temp file
- Tune `--workers` based on available RAM: `max_workers = max(1, available_ram_gb // 2)`
- Default to conservative worker count (e.g., 4 max) and document memory guidance

**Phase:** Phase 1 (pipeline) and Phase 2 (batch config)

---

### 2. Wrong DPI in ALTO Coordinates

**Risk:** HIGH — the most common cause of ALTO files that look correct but display wrong in Goobi/Kitodo (words highlighted in wrong positions).

**Warning signs:**
- Word highlights in DFG Viewer are consistently offset or scaled
- ALTO coordinates look plausible (small numbers) but don't match page

**Root causes:**
- TIFF has no DPI tag → pytesseract defaults to 70 DPI → grossly wrong coordinates
- Crop is applied but DPI recalculated relative to original rather than crop
- ALTO uses pixels instead of mm10 (wrong `MeasurementUnit`)

**Prevention:**
- Always extract DPI from TIFF before processing: `image.info.get('dpi', (300.0, 300.0))`
- If DPI is missing, default to 300 DPI and log a warning (do NOT silently default to 72 or 96)
- Pass DPI to Tesseract: `pytesseract.image_to_alto_xml(img, config=f'--dpi {int(dpi_x)}')`
- Verify `MeasurementUnit` in ALTO output is `mm10` or `pixel` (consistent with coordinates)
- Write a coordinate sanity check: first word on page should have HPOS/VPOS > 0 and < page width

**Phase:** Phase 1 (pipeline)

---

### 3. ALTO Namespace Mismatch (ALTO 3.x vs 2.1)

**Risk:** HIGH — Tesseract and pytesseract output ALTO 3.x namespace by default. Goobi/Kitodo expects ALTO 2.1 (`xmlns="http://schema.ccs-gmbh.com/ALTO"`). The files will fail schema validation and may be silently rejected or display incorrectly.

**Warning signs:**
- Goobi ingest rejects ALTO files or shows no fulltext
- `xmlns="http://www.loc.gov/standards/alto/ns-v3#"` in output files

**Prevention:**
- Parse every Tesseract ALTO output with lxml and rewrite the namespace before writing to disk
- Validate against ALTO 2.1 XSD during development on a sample file
- Add a namespace assertion to the test suite

**Phase:** Phase 1 (ALTOBuilder component)

---

### 4. Crop Detection Failure on Edge Cases

**Risk:** MEDIUM — contour-based detection assumes a dark scan background. Some scans may have very light borders, pages with mostly white margins, or color calibration charts.

**Warning signs:**
- Crop box is smaller than 30% of original image (crop too aggressive)
- Crop box is 99%+ of original (detection missed, no border removed)
- Content is cut off (text at page edge is missing in ALTO)

**Prevention:**
- Add a fallback: if `detected_area / original_area < 0.4` or `> 0.98`, use original image bounds
- Add configurable `--padding PX` to add margin around detected boundary (default 50px)
- Log when fallback is triggered so operator can inspect
- Test with 10-20 representative samples before running the full batch

**Phase:** Phase 1 (CropDetector), Phase 3 (robustness)

---

### 5. Parallel Worker Crashes Losing Progress

**Risk:** MEDIUM — if the main process crashes (power cut, OOM on orchestrator), progress of completed files is lost if skip-logic relies on in-memory state only.

**Warning signs:**
- Rerunning the batch reprocesses everything from scratch
- Operator can't tell which files succeeded in a partial run

**Prevention:**
- Skip logic must check for file existence on disk, not in-memory state — rerun is safe by design
- Write output file atomically: write to `.xml.tmp`, then rename to `.xml` — prevents corrupt half-written files being skipped on rerun
- Log completed files to a run log (`batch_run_YYYYMMDD_HHMMSS.log`) for audit

**Phase:** Phase 2 (batch orchestration)

---

### 6. Tesseract Language Pack Not Installed

**Risk:** MEDIUM — if `tesseract-ocr-deu` is not installed, Tesseract silently falls back to English or errors. Output ALTO files will have garbage OCR but valid XML structure.

**Warning signs:**
- OCR output contains many non-German characters or nonsense words
- Tesseract log: `Error, could not initialize tesseract`

**Prevention:**
- Check at startup: `subprocess.run(['tesseract', '--list-langs'])` and verify `deu` is present
- Fail fast with a clear error message if language pack missing: `"deu language pack not installed. Run: apt install tesseract-ocr-deu"`
- Document installation requirements prominently in README

**Phase:** Phase 2 (CLI / startup validation)

---

### 7. Coordinate Offset After Cropping

**Risk:** MEDIUM — a subtle but important correctness issue. Tesseract reports coordinates relative to the image it received (the cropped image). If you later need to reference coordinates back to the original scan, you need the crop offset. For ALTO display in Goobi, the coordinates should match the image that Goobi displays — if Goobi displays the cropped image, this is correct. If Goobi displays the original, offset correction is needed.

**Warning signs:**
- Fulltext search highlighting offset by exactly the crop margin

**Prevention:**
- Clarify with the operator: does Goobi display the original TIFF or the cropped version?
- For this project (originals untouched, crop is intermediate only), Goobi will display the **original** TIFF
- Therefore ALTO coordinates must be offset by the crop box: `HPOS += crop_x`, `VPOS += crop_y`
- This offset correction must happen in ALTOBuilder before writing

**Phase:** Phase 1 (ALTOBuilder) — CRITICAL correctness issue

---

### 8. Output Directory Not Created

**Risk:** LOW but annoying — if the output `alto/` subdirectory doesn't exist, file write fails with a cryptic error in the worker process.

**Prevention:**
- Create output directory at startup (before dispatching workers): `output_dir.mkdir(parents=True, exist_ok=True)`

**Phase:** Phase 2 (CLI)
