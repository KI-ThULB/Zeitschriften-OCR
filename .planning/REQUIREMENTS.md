# Requirements: Zeitschriften-OCR

**Defined:** 2026-02-27
**Core Value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.

## v1.4 Requirements

### File Ingestion

- [ ] **INGEST-01**: User can drag individual TIFF files onto the app to queue them for OCR processing
- [ ] **INGEST-02**: User can see the list of queued TIFFs before starting processing
- [ ] **INGEST-03**: User can remove a file from the queue before processing starts

### OCR Processing

- [ ] **PROC-01**: User can start OCR processing on all queued TIFFs with a single button
- [ ] **PROC-02**: User sees live progress while OCR runs (files done / total / percentage / ETA)
- [x] **PROC-03**: Already-processed TIFFs in the queue are skipped automatically (same skip logic as CLI)
- [x] **PROC-04**: Processing errors per file are shown in the UI without stopping the batch

### Viewer

- [x] **VIEW-01**: User can browse all previously processed files in a file list panel
- [x] **VIEW-02**: Clicking a file shows the TIFF rendered as an image in the left panel
- [x] **VIEW-03**: Clicking a file shows the OCR text in the right panel, extracted word-by-word from the ALTO XML
- [x] **VIEW-04**: User can navigate to the previous/next file with keyboard or buttons

### Word Overlay

- [x] **OVLY-01**: Clicking a word in the text panel highlights its bounding box on the TIFF image
- [x] **OVLY-02**: Bounding box coordinates scale correctly as the image is resized

### Post-Correction

- [ ] **EDIT-01**: User can click a word in the text panel to select it for editing
- [ ] **EDIT-02**: User can type a corrected word and confirm the edit
- [ ] **EDIT-03**: Saving a correction overwrites the ALTO XML Word element and validates the file before writing
- [ ] **EDIT-04**: User sees visual confirmation when a correction is saved

## Future Requirements

### Usability Enhancements

- **UX-01**: Word confidence coloring — shade words by ALTO @WC value (red/yellow/green)
- **UX-02**: Keyboard navigation through words for sequential correction
- **UX-03**: Resizable left/right panels
- **UX-04**: Undo last correction

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user / authentication | Local single-operator tool — no security benefit |
| ALTO structural editing (merge/split words) | Different problem class from content correction; extreme complexity |
| Coordinate editing | Wrong tool — coordinates come from Tesseract; re-run OCR to change them |
| Re-OCR on selected regions | High complexity, low gain vs. typing the correct word |
| Remote deployment / hosting | Local workstation tool only |
| Mobile / responsive layout | Desktop operator tool |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGEST-01 | Phase 13 | Pending |
| INGEST-02 | Phase 13 | Pending |
| INGEST-03 | Phase 13 | Pending |
| PROC-01 | Phase 13 | Pending |
| PROC-02 | Phase 13 | Pending |
| PROC-03 | Phase 9 | Complete |
| PROC-04 | Phase 9 | Complete |
| VIEW-01 | Phase 11 | Complete |
| VIEW-02 | Phase 10 | Complete |
| VIEW-03 | Phase 10 | Complete |
| VIEW-04 | Phase 11 | Complete |
| OVLY-01 | Phase 11 | Complete |
| OVLY-02 | Phase 11 | Complete |
| EDIT-01 | Phase 12 | Pending |
| EDIT-02 | Phase 12 | Pending |
| EDIT-03 | Phase 12 | Pending |
| EDIT-04 | Phase 12 | Pending |

**Coverage:**
- v1.4 requirements: 17 total
- Mapped to phases: 17 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-27*
*Last updated: 2026-02-27 after roadmap creation (phases 9–13)*
