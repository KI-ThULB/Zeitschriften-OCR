# Zeitschriften-OCR

## What This Is

A batch processing pipeline for digitized journal and magazine scans. It takes several hundred large archival TIFF files (117–240 MB each), automatically crops away scanner borders, runs Tesseract OCR, and writes one ALTO 2.1 XML file per TIFF — ready for ingest into Goobi/Kitodo-based digital library systems and display in the DFG Viewer.

## Core Value

Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Auto-detect and crop scan borders/margins from each TIFF (OpenCV contour detection)
- [ ] Run Tesseract OCR on the cropped image with German language model
- [ ] Output one ALTO 2.1 XML file per TIFF to a sibling output folder
- [ ] Process files in parallel to handle hundreds of large TIFFs efficiently
- [ ] Skip already-processed TIFFs on rerun (idempotent batch)
- [ ] Originals remain untouched; cropped TIFFs are intermediate only (not saved)
- [ ] CLI invocation: user specifies input folder and output folder

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
- Starting from scratch — no existing scripts or tooling

## Constraints

- **Format**: ALTO 2.1 XML — mandated by Goobi/Kitodo ingest pipeline
- **OCR engine**: Tesseract — open source, established in German library workflows
- **Language model**: `deu` (German) Tesseract trained data
- **Originals**: Must never be modified or overwritten
- **Output layout**: `<output_dir>/alto/<filename>.xml` alongside input folder

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Tesseract for OCR | Open source, standard in German digital library ecosystem, good `deu` model | — Pending |
| OpenCV for crop detection | Robust contour/edge detection for scanner border removal | — Pending |
| Skip-if-exists for reruns | Prevents reprocessing hundreds of large files after partial failure | — Pending |
| Parallel processing | Files are independent; parallelism essential for hundreds of 200 MB TIFFs | — Pending |

---
*Last updated: 2026-02-24 after initialization*
