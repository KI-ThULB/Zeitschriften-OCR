# Roadmap: Zeitschriften-OCR

## Milestones

- ✅ **v1.0 Single-File Pipeline** — Phase 1 (shipped 2026-02-24)
- ✅ **v1.1 Batch Processor** — Phases 2–3 (shipped 2026-02-25)
- ✅ **v1.2 Image Preprocessing** — Phases 4–5 (shipped 2026-02-25)
- ✅ **v1.3 Operator Experience** — Phases 6–8 (shipped 2026-02-26)
- 🚧 **v1.4 Web Viewer** — Phases 9–13 (in progress)

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

### 🚧 v1.4 Web Viewer (In Progress)

**Milestone Goal:** A local Flask web app that wraps the OCR pipeline — drag-and-drop TIFF upload, live progress monitoring, side-by-side TIFF+text viewer with SVG word overlays, and word-level ALTO XML post-correction.

- [x] **Phase 9: Flask Foundation and Job State** - Bootable app.py with background OCR thread, SSE stream, and per-file skip/error isolation (2 plans) — completed 2026-02-27
- [x] **Phase 10: TIFF and ALTO Data Endpoints** - JPEG proxy endpoint and ALTO coordinate JSON API for viewer (completed 2026-02-27)
- [x] **Phase 11: Side-by-Side Viewer UI** - File browser, two-panel TIFF+text layout, SVG word bounding box overlay with click cross-reference (completed 2026-02-28)
- [ ] **Phase 12: Word Correction** - Inline word editing, atomic ALTO XML save with XSD validation gate
- [ ] **Phase 13: Upload UI and Live Progress** - Drag-and-drop upload zone, queue management, SSE-driven progress display, end-to-end integration

## Phase Details

### Phase 9: Flask Foundation and Job State
**Goal**: A bootable `app.py` with the correct threading/SSE concurrency model, background OCR worker, and per-file error isolation — verified against real TIFFs before any UI is built
**Depends on**: Phase 8 (existing pipeline.py with process_tiff, load_xsd, validate_alto_file)
**Requirements**: PROC-03, PROC-04
**Success Criteria** (what must be TRUE):
  1. `python app.py` starts without error and serves on localhost:5000
  2. POST /upload accepts a TIFF and stages it; POST /run starts OCR in a background thread (returns 202 immediately, does not block the request)
  3. GET /stream delivers SSE events for each completed file during a multi-TIFF OCR run (events arrive while OCR is running, not after)
  4. An already-processed TIFF submitted to the queue is skipped automatically, matching CLI skip-if-exists behavior
  5. A TIFF that fails OCR is reported as an error without stopping processing of remaining queued files
**Plans**: 2 plans

Plans:
- [x] 09-01-PLAN.md — TDD: test scaffold for PROC-03 (skip logic) and PROC-04 (error isolation) — RED tests
- [x] 09-02-PLAN.md — Implement app.py Flask server; make tests GREEN

### Phase 10: TIFF and ALTO Data Endpoints
**Goal**: `GET /image/<stem>` serves a scaled JPEG of the TIFF and `GET /alto/<stem>` returns a flat word array with page dimensions and per-word bounding box coordinates — both verified against real 200 MB TIFFs before the viewer is built
**Depends on**: Phase 9
**Requirements**: VIEW-02, VIEW-03
**Success Criteria** (what must be TRUE):
  1. GET /image/<stem> returns a JPEG renderable by a browser for any TIFF in the output folder, including landscape orientation
  2. GET /alto/<stem> returns JSON with page_width, page_height, jpeg_width, jpeg_height, and a word array containing hpos/vpos/width/height/confidence/id for every word in the ALTO XML
  3. Scale factors computed from the response (renderedWidth / page_width) produce overlays that land on the correct word at three different browser window widths
**Plans**: TBD

### Phase 11: Side-by-Side Viewer UI
**Goal**: A two-panel viewer page showing the TIFF image on the left and OCR word text on the right, with SVG bounding box overlays and bidirectional click cross-reference between text and image
**Depends on**: Phase 10
**Requirements**: VIEW-01, VIEW-04, OVLY-01, OVLY-02
**Success Criteria** (what must be TRUE):
  1. The viewer lists all previously processed files; clicking a filename loads that file without a full page reload
  2. The left panel shows the TIFF rendered as a JPEG; the right panel shows every OCR word as a clickable text element
  3. Clicking a word in the text panel draws a highlight rectangle over the corresponding bounding box on the TIFF image
  4. Bounding box positions remain correct after the browser window is resized (overlay recomputes from live rendered image dimensions)
  5. Previous/next buttons and keyboard arrow keys navigate to the adjacent file in the list
**Plans**: 2 plans

Plans:
- [ ] 11-01-PLAN.md — Add GET /files and GET / routes to app.py, tests, and templates/viewer.html stub
- [ ] 11-02-PLAN.md — Implement complete viewer.html (layout, file loading, SVG overlay, navigation)

### Phase 12: Word Correction
**Goal**: Operators can click any word in the text panel, type a correction, and save it — with the ALTO XML overwritten atomically only after XSD validation passes
**Depends on**: Phase 11
**Requirements**: EDIT-01, EDIT-02, EDIT-03, EDIT-04
**Success Criteria** (what must be TRUE):
  1. Clicking a word in the text panel replaces it with an editable input field pre-filled with the current OCR text
  2. Pressing Enter or clicking Save writes the corrected word to the ALTO XML file on disk and the text panel reflects the new value
  3. The ALTO XML file is not overwritten if post-edit XSD validation fails; the browser receives an error message instead
  4. A visible confirmation indicator appears after a successful save (input returns to text, no page reload required)
**Plans**: TBD

### Phase 13: Upload UI and Live Progress
**Goal**: A drag-and-drop upload interface with a visible file queue, a Start button that triggers OCR, and a live progress bar fed by the SSE stream — completing the full operator workflow end-to-end
**Depends on**: Phase 9, Phase 11 (viewer linked from progress results)
**Requirements**: INGEST-01, INGEST-02, INGEST-03, PROC-01, PROC-02
**Success Criteria** (what must be TRUE):
  1. Dragging one or more TIFF files onto the upload zone adds them to a visible queue list without starting OCR
  2. Individual files can be removed from the queue before processing starts
  3. Clicking the Start button triggers OCR on all queued files; the button is disabled while processing is running
  4. A progress bar and status line update in real time showing files completed / total / percentage / ETA as OCR runs
  5. Completed files appear as links in the results list and clicking one opens the side-by-side viewer for that file
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
| 9. Flask Foundation and Job State | v1.4 | Complete    | 2026-02-27 | 2026-02-27 |
| 10. TIFF and ALTO Data Endpoints | 2/2 | Complete    | 2026-02-27 | - |
| 11. Side-by-Side Viewer UI | 2/2 | Complete    | 2026-02-28 | - |
| 12. Word Correction | v1.4 | 0/TBD | Not started | - |
| 13. Upload UI and Live Progress | v1.4 | 0/TBD | Not started | - |
