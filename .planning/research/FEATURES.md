# Features Research: TIFF Batch OCR → ALTO XML Pipeline

## Table Stakes

Features a batch OCR pipeline must have to be usable in a digital library production context.

### Batch Processing
- **Process all TIFFs in a folder** — find and queue all `.tif`/`.tiff` files recursively or flat
- **Skip already-processed files** — check for existing ALTO XML before processing; safe to rerun
- **Progress reporting** — show current file, count completed, count remaining
- Complexity: Low

### Image Preprocessing
- **Border/margin removal** — detect and crop scanner artifacts before OCR; critical for coordinate accuracy
- **DPI preservation** — read DPI from TIFF metadata and pass to Tesseract for correct mm-to-pixel conversion in ALTO
- Complexity: Medium

### OCR
- **Configurable language** — `deu` as default, overridable via CLI
- **Configurable page segmentation mode** — `--psm` passthrough for different scan types
- Complexity: Low

### ALTO Output
- **ALTO 2.1 XML per TIFF** — one output file per input file, matching filename
- **Word-level bounding boxes** — coordinates relative to the cropped image (not the original)
- **Schema-valid output** — validates against ALTO 2.1 XSD before writing
- **Correct namespace** — `xmlns="http://schema.ccs-gmbh.com/ALTO"` (not ALTO 3.x)
- Complexity: Medium

### Error Handling
- **Per-file error isolation** — one broken TIFF must not stop the batch
- **Error log file** — record failed files with error message and stack trace
- **Continue on failure** — batch completes even if individual files fail
- Complexity: Low-Medium

### CLI Interface
- `--input DIR` — input folder with TIFFs
- `--output DIR` — output folder for ALTO files
- `--workers N` — parallel worker count (default: CPU count)
- `--force` — reprocess even if ALTO already exists
- Complexity: Low

## Differentiators

Features that improve quality and usability but aren't blockers.

### Preprocessing Quality
- **Deskew detection** — detect and correct slight rotation before OCR (improves word bbox accuracy)
- **Adaptive thresholding** — improve binarization for uneven scan illumination
- **Crop padding configuration** — `--padding PX` to add margin around detected content area

### Reporting
- **Summary report** — JSON or CSV with per-file: input path, output path, duration, word count, error
- **Timing statistics** — total time, average per file, estimated remaining

### Validation
- **ALTO schema validation** — validate each output against XSD and log failures without aborting
- **Coordinate sanity check** — verify all word boxes fall within page dimensions

### Operational
- **Dry run mode** — `--dry-run` shows what would be processed without doing it
- **Verbose logging** — `--verbose` for per-file Tesseract output

## Anti-Features (Deliberately Out of Scope for v1)

| Feature | Why Excluded |
|---------|-------------|
| GUI or web interface | CLI tool for batch/server use; GUI adds complexity with no batch benefit |
| ALTO 3.x / 4.x output | Target system requires 2.1; adding versions fragments validation logic |
| Database tracking | Flat file skip-check (existence of output file) is sufficient and simpler |
| Multi-language OCR | Single-language per run is sufficient; `--lang` flag covers edge cases |
| PDF input/output | Input is TIFF only; ALTO is the output format |
| Image quality scoring | Out of scope for v1; crop + OCR quality judged by downstream Goobi review |
| Goobi/Kitodo plugin | Standalone CLI; integration handled at ingest level by existing Goobi workflows |
| Cloud/distributed processing | Local batch tool; hundreds of files is manageable on a single machine |

## Feature Dependencies

```
DPI preservation → ALTO coordinate correctness (blocking dependency)
Border detection → must run BEFORE OCR (coordinates change after crop)
Per-file isolation → required before parallelism (errors must not cascade)
ALTO namespace fix → required for Goobi/Kitodo ingest
```
