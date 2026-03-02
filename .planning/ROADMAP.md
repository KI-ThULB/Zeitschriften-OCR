# Roadmap: Zeitschriften-OCR

## Milestones

- ✅ **v1.0 Single-File Pipeline** — Phase 1 (shipped 2026-02-24)
- ✅ **v1.1 Batch Processor** — Phases 2–3 (shipped 2026-02-25)
- ✅ **v1.2 Image Preprocessing** — Phases 4–5 (shipped 2026-02-25)
- ✅ **v1.3 Operator Experience** — Phases 6–8 (shipped 2026-02-26)
- ✅ **v1.4 Web Viewer** — Phases 9–11 (shipped 2026-02-28)
- ✅ **v1.5 Web Viewer Complete** — Phases 12–18 (shipped 2026-03-02)
- 🚧 **v1.6 Structured Text & TEI Export** — Phases 19–21 (in progress)

---

## Phases

<details>
<summary>✅ v1.0 Single-File Pipeline — SHIPPED 2026-02-24</summary>

- [x] Phase 1: Single-File Pipeline (2/2 plans) — completed 2026-02-24

See archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Batch Processor — SHIPPED 2026-02-25</summary>

- [x] Phase 2: Batch Orchestration and CLI (2/2 plans) — completed 2026-02-24
- [x] Phase 3: Validation and Reporting (2/2 plans) — completed 2026-02-25

See archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Image Preprocessing — SHIPPED 2026-02-25</summary>

- [x] Phase 4: Deskew (1/1 plans) — completed 2026-02-25
- [x] Phase 5: Adaptive Thresholding (1/1 plans) — completed 2026-02-25

See archive: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Operator Experience — SHIPPED 2026-02-26</summary>

- [x] Phase 6: Diagnostic Flags (2/2 plans) — completed 2026-02-26
- [x] Phase 7: Live Progress Display (1/1 plans) — completed 2026-02-26
- [x] Phase 8: Config File Support (2/2 plans) — completed 2026-02-26

See archive: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 Web Viewer — SHIPPED 2026-02-28</summary>

- [x] Phase 9: Flask Foundation and Job State (2/2 plans) — completed 2026-02-27
- [x] Phase 10: TIFF and ALTO Data Endpoints (2/2 plans) — completed 2026-02-27
- [x] Phase 11: Side-by-Side Viewer UI (2/2 plans) — completed 2026-02-28

See archive: `.planning/milestones/v1.4-ROADMAP.md`

</details>

<details>
<summary>✅ v1.5 Web Viewer Complete — SHIPPED 2026-03-02</summary>

- [x] Phase 12: Word Correction (2/2 plans) — completed 2026-03-01
- [x] Phase 13: Upload UI and Live Progress (2/2 plans) — completed 2026-03-01
- [x] Phase 14: Viewer Zoom and Pan (1/1 plans) — completed 2026-03-01
- [x] Phase 15: VLM Article Segmentation (2/2 plans) — completed 2026-03-01
- [x] Phase 16: METS/MODS Output (2/2 plans) — completed 2026-03-01
- [x] Phase 17: VLM Settings UI (2/2 plans) — completed 2026-03-02
- [x] Phase 18: Article Browser and Full-Text Search (2/2 plans) — completed 2026-03-02

See archive: `.planning/milestones/v1.5-ROADMAP.md`

</details>

### v1.6 Structured Text & TEI Export (In Progress)

**Milestone Goal:** Transform raw OCR word streams into structured, readable text and export full scholarly TEI P5 XML with facsimile links.

- [x] **Phase 19: Text Normalization** — Column reading order, hyphenation rejoining, confidence marking (completed 2026-03-02)
- [ ] **Phase 20: Structure Detection and Viewer** — Paragraph detection, role annotation, structured viewer display
- [ ] **Phase 21: TEI P5 Export** — TEI document generation with article divs, line/page elements, facsimile section

## Phase Details

### Phase 19: Text Normalization
**Goal**: Users see a clean, correctly ordered word stream — columns read left-to-right, hyphens rejoined, low-confidence words visually flagged
**Depends on**: Phase 18 (existing ALTO word JSON endpoint and text panel)
**Requirements**: TEXT-01, TEXT-02, TEXT-03
**Success Criteria** (what must be TRUE):
  1. User views a two-column scan in the text panel and words appear in left-column-first order, not interleaved top-to-bottom across both columns
  2. A word split across a line ending with a hyphen (e.g. "Ver-" + "bindung") appears as the rejoined form "Verbindung" in the text panel
  3. User can set a word-confidence threshold in the viewer; words below it appear visually distinct (faded or marked) so low-quality OCR regions are immediately obvious
  4. The original per-word ALTO XML is unchanged — normalization is display-only, not written back to XML
**Plans:** 2/2 plans complete

Plans:
- [ ] 19-01-PLAN.md — Extend serve_alto() with blocks array and line_end flag; add TestAltoEndpoint tests
- [ ] 19-02-PLAN.md — Client-side normalizeWords() pipeline, confidence slider, and WC badge in viewer.html

### Phase 20: Structure Detection and Viewer
**Goal**: Users see text organized into labeled paragraphs and headings rather than a flat word list, with structural roles derived from VLM article data
**Depends on**: Phase 19 (normalized word stream), Phase 15 (VLM article segment JSON)
**Requirements**: STRUCT-07, STRUCT-08, VIEW-07
**Success Criteria** (what must be TRUE):
  1. User views a multi-paragraph page and the text panel shows paragraph breaks at points where ALTO line-spacing gaps exceed the median line height — paragraphs are visually separated, not run together
  2. User can see each text block labelled with its structural role (heading, paragraph, caption, or advertisement) derived from the VLM article segmentation regions stored per page
  3. Headings render with prominent styling (bold, larger size) in the text panel so article structure is readable at a glance without needing to consult the TIFF image
  4. Structural role labels and paragraph grouping persist correctly when the user navigates to a different file via the sidebar
**Plans**: TBD

### Phase 21: TEI P5 Export
**Goal**: Users can download a single TEI P5 XML file per issue that encodes article structure, text with line and page markers, and facsimile coordinates — ready for scholarly use
**Depends on**: Phase 19 (normalized text), Phase 20 (structural roles), Phase 15 (article segment regions)
**Requirements**: TEI-01, TEI-02, TEI-03
**Success Criteria** (what must be TRUE):
  1. User triggers TEI export and receives a well-formed TEI P5 XML document where each VLM-identified article appears as a `<div type="article">` element with `@n` and title metadata
  2. The TEI document contains `<lb/>` elements at each OCR line boundary and `<pb n="N" facs="#page-N"/>` elements at each page transition, linking text to the correct JPEG image
  3. The TEI document contains a `<facsimile>` section with one `<surface xml:id="page-N">` per page and `<zone>` elements per article region carrying ALTO-derived coordinate attributes (x, y, width, height)
  4. Exported TEI validates as well-formed XML and the `facs` references in `<pb>` correctly resolve to `xml:id` values in the `<facsimile>` section
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Single-File Pipeline | v1.0 | 2/2 | Complete | 2026-02-24 |
| 2. Batch Orchestration and CLI | v1.1 | 2/2 | Complete | 2026-02-24 |
| 3. Validation and Reporting | v1.1 | 2/2 | Complete | 2026-02-25 |
| 4. Deskew | v1.2 | 1/1 | Complete | 2026-02-25 |
| 5. Adaptive Thresholding | v1.2 | 1/1 | Complete | 2026-02-25 |
| 6. Diagnostic Flags | v1.3 | 2/2 | Complete | 2026-02-26 |
| 7. Live Progress Display | v1.3 | 1/1 | Complete | 2026-02-26 |
| 8. Config File Support | v1.3 | 2/2 | Complete | 2026-02-26 |
| 9. Flask Foundation and Job State | v1.4 | 2/2 | Complete | 2026-02-27 |
| 10. TIFF and ALTO Data Endpoints | v1.4 | 2/2 | Complete | 2026-02-27 |
| 11. Side-by-Side Viewer UI | v1.4 | 2/2 | Complete | 2026-02-28 |
| 12. Word Correction | v1.5 | 2/2 | Complete | 2026-03-01 |
| 13. Upload UI and Live Progress | v1.5 | 2/2 | Complete | 2026-03-01 |
| 14. Viewer Zoom and Pan | v1.5 | 1/1 | Complete | 2026-03-01 |
| 15. VLM Article Segmentation | v1.5 | 2/2 | Complete | 2026-03-01 |
| 16. METS/MODS Output | v1.5 | 2/2 | Complete | 2026-03-01 |
| 17. VLM Settings UI | v1.5 | 2/2 | Complete | 2026-03-02 |
| 18. Article Browser and Full-Text Search | v1.5 | 2/2 | Complete | 2026-03-02 |
| 19. Text Normalization | 2/2 | Complete   | 2026-03-02 | - |
| 20. Structure Detection and Viewer | v1.6 | 0/TBD | Not started | - |
| 21. TEI P5 Export | v1.6 | 0/TBD | Not started | - |
