# Requirements: Zeitschriften-OCR

**Defined:** 2026-02-28
**Core Value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.

## v1.5 Requirements

### Post-Correction

- [x] **EDIT-01**: User can click a word in the text panel to select it for editing
- [x] **EDIT-02**: User can type a corrected word and confirm the edit
- [x] **EDIT-03**: Saving a correction overwrites the ALTO XML Word element and validates the file before writing
- [x] **EDIT-04**: User sees visual confirmation when a correction is saved

### File Ingestion

- [x] **INGEST-01**: User can drag individual TIFF files onto the app to queue them for OCR processing
- [x] **INGEST-02**: User can see the list of queued TIFFs before starting processing
- [x] **INGEST-03**: User can remove a file from the queue before processing starts

### OCR Processing

- [x] **PROC-01**: User can start OCR processing on all queued TIFFs with a single button
- [x] **PROC-02**: User sees live progress while OCR runs (files done / total / percentage / ETA)

### Viewer Zoom

- [x] **VIEW-05**: User can zoom in/out on the TIFF image using mouse wheel; SVG word overlay stays aligned at all zoom levels
- [x] **VIEW-06**: User can pan the zoomed image by clicking and dragging

### Article Structuring

- [ ] **STRUCT-01**: User can trigger automatic article segmentation for any page via a configurable VLM/LLM provider (provider and model set via config file or `--vlm-provider` / `--vlm-model` CLI flags)
- [x] **STRUCT-02**: The system identifies article regions on each page (bounding box, type: headline / article / advertisement / illustration / caption) and stores results per page
- [ ] **STRUCT-03**: Each identified article gets a title and section type extracted and made accessible as structured metadata
- [x] **STRUCT-04**: Structured output is written as a METS/MODS logical structure document with article-level `<div>` elements linked to ALTO word coordinates (DFG Viewer / Goobi-Kitodo newspaper ingest profile)
- [x] **STRUCT-05**: User can browse identified articles for a page in the viewer sidebar — clicking an article highlights its region on the TIFF image
- [x] **STRUCT-06**: User can perform full-text search across all structured articles by title or content from the web interface

## Future Requirements

### Usability Enhancements

- **UX-01**: Word confidence coloring — shade words by ALTO @WC value (red/yellow/green)
- **UX-02**: Keyboard navigation through words for sequential correction
- **UX-03**: Resizable left/right panels
- **UX-04**: Undo last correction

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user / authentication | Local single-operator tool |
| ALTO structural editing (merge/split words) | Different problem class; extreme complexity |
| Coordinate editing | Coordinates come from Tesseract; re-run OCR |
| Re-OCR on selected regions | High complexity, low gain |
| Remote deployment / hosting | Local workstation tool only |
| Mobile / responsive layout | Desktop operator tool |
| Automatic OCR quality scoring | Out of scope for this milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| EDIT-01 | Phase 12 | Complete |
| EDIT-02 | Phase 12 | Complete |
| EDIT-03 | Phase 12 | Complete |
| EDIT-04 | Phase 12 | Complete |
| INGEST-01 | Phase 13 | Complete |
| INGEST-02 | Phase 13 | Complete |
| INGEST-03 | Phase 13 | Complete |
| PROC-01 | Phase 13 | Complete |
| PROC-02 | Phase 13 | Complete |
| VIEW-05 | Phase 14 | Complete |
| VIEW-06 | Phase 14 | Complete |
| STRUCT-01 | Phase 15 | Pending |
| STRUCT-02 | Phase 15 | Complete |
| STRUCT-03 | Phase 15 | Pending |
| STRUCT-04 | Phase 16 | Complete |
| STRUCT-05 | Phase 17 | Complete |
| STRUCT-06 | Phase 17 | Complete |

**Coverage:**
- v1.5 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after v1.5 roadmap creation*
