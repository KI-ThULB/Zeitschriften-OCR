# Requirements: Zeitschriften-OCR

**Defined:** 2026-03-02
**Core Value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.

## v1.6 Requirements

### Text Normalization

- [x] **TEXT-01**: User sees ALTO words delivered in correct multi-column reading order — left-to-right across columns (detected from TextBlock HPOS), then top-to-bottom within each column
- [x] **TEXT-02**: System detects and rejoins German end-of-line hyphenated words (e.g. "Ver-" + "bindung" → "Verbindung") for display in the text panel and TEI export, preserving the original split form in ALTO
- [x] **TEXT-03**: User can configure a minimum word-confidence threshold; words below it are visually marked (e.g. faded) in the text panel so low-quality OCR regions are obvious at a glance

### Structure Detection

- [x] **STRUCT-07**: System groups ALTO words into paragraphs by detecting line-spacing gaps larger than the median line height, producing paragraph-separated text instead of a flat word stream
- [x] **STRUCT-08**: System annotates detected text blocks with a structural role (heading / paragraph / caption / advertisement) derived from existing VLM article segmentation regions, stored per page

### Viewer

- [ ] **VIEW-07**: Viewer renders structured text — headings styled prominently (bold, larger size), paragraphs separated by whitespace — replacing the current flat word list in the text panel

### TEI Export

- [ ] **TEI-01**: System generates a TEI P5 XML document per processed issue combining all pages; each VLM-identified article appears as a `<div type="article">` with `@n` and title metadata
- [ ] **TEI-02**: TEI document preserves line structure via `<lb/>` elements and page transitions via `<pb n="N" facs="#page-N"/>` elements linked to JPEG images
- [ ] **TEI-03**: TEI document includes a `<facsimile>` section with one `<surface xml:id="page-N">` per page and `<zone>` elements for each article region carrying ALTO-derived coordinate attributes

## Future Requirements

### Usability Enhancements (from v1.5)

- **UX-01**: Word confidence coloring — shade words by ALTO @WC value (red/yellow/green gradient)
- **UX-02**: Keyboard navigation through words for sequential correction
- **UX-03**: Resizable left/right panels
- **UX-04**: Undo last correction

### Possible v1.7+

- **TEXT-04**: Re-join OCR segments across columns to produce fully linearized article text suitable for NLP pipelines
- **TEI-04**: TEI document includes machine-readable `<choice><orig>Ver-</orig><reg>Verbindung</reg></choice>` elements for each rejoined hyphenation
- **TEI-05**: Export endpoint for individual articles as standalone TEI fragments
- **STRUCT-09**: User can manually override the detected structural role for a text block in the viewer

## Out of Scope

| Feature | Reason |
|---------|--------|
| ALTO 3.x / 4.x structural extensions | Target remains ALTO 2.1 for Goobi/Kitodo compatibility |
| Re-OCR on selected regions | High complexity, low gain |
| ALTO structural editing (merge/split words) | Different problem class; extreme complexity |
| Remote TEI hosting / IIIF manifest | Local workstation tool only |
| Languages other than German | Pipeline optimized for modern German text |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEXT-01 | Phase 19 | Complete |
| TEXT-02 | Phase 19 | Complete |
| TEXT-03 | Phase 19 | Complete |
| STRUCT-07 | Phase 20 | Complete |
| STRUCT-08 | Phase 20 | Complete |
| VIEW-07 | Phase 20 | Pending |
| TEI-01 | Phase 21 | Pending |
| TEI-02 | Phase 21 | Pending |
| TEI-03 | Phase 21 | Pending |

**Coverage:**
- v1.6 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

---
*Requirements defined: 2026-03-02*
*Last updated: 2026-03-02 after milestone v1.6 start*
