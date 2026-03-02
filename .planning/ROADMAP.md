# Roadmap: Zeitschriften-OCR

## Milestones

- ✅ **v1.0 Single-File Pipeline** — Phase 1 (shipped 2026-02-24)
- ✅ **v1.1 Batch Processor** — Phases 2–3 (shipped 2026-02-25)
- ✅ **v1.2 Image Preprocessing** — Phases 4–5 (shipped 2026-02-25)
- ✅ **v1.3 Operator Experience** — Phases 6–8 (shipped 2026-02-26)
- ✅ **v1.4 Web Viewer** — Phases 9–11 (shipped 2026-02-28)
- 🚧 **v1.5 Web Viewer Complete** — Phases 12–17 (planned)

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

### 🚧 v1.5 Web Viewer Complete (Planned)

**Milestone Goal:** Complete the full web operator workflow — inline word correction with atomic ALTO XML save, drag-and-drop TIFF upload, live SSE progress display, viewer zoom/pan, VLM-powered article segmentation with METS/MODS output, and full-text article search.

- [x] **Phase 12: Word Correction** — Inline word editing, atomic ALTO XML save with XSD validation gate (completed 2026-02-28)
- [x] **Phase 13: Upload UI and Live Progress** — Drag-and-drop upload zone, queue management, SSE-driven progress display, end-to-end integration (completed 2026-03-01)
- [x] **Phase 14: Viewer Zoom and Pan** — Mouse-wheel zoom with aligned SVG overlay, click-and-drag pan (completed 2026-03-01)
- [ ] **Phase 15: VLM Article Segmentation** — Configurable VLM/LLM provider, region detection, article metadata extraction
- [ ] **Phase 16: METS/MODS Output** — Logical structure document per DFG Viewer / Goobi-Kitodo newspaper ingest profile
- [ ] **Phase 17: Article Browser and Full-Text Search** — Viewer sidebar with article list and region highlight, SQLite FTS5 search

## Phase Details

### Phase 12: Word Correction
**Goal**: Operators can click any word in the text panel, type a correction, and save it — with the ALTO XML overwritten atomically only after XSD validation passes
**Depends on**: Phase 11
**Requirements**: EDIT-01, EDIT-02, EDIT-03, EDIT-04
**Success Criteria** (what must be TRUE):
  1. Clicking a word in the text panel replaces it with an editable input field pre-filled with the current OCR text
  2. Pressing Enter or clicking Save writes the corrected word to the ALTO XML file on disk and the text panel reflects the new value without a page reload
  3. The ALTO XML file is not overwritten if post-edit XSD validation fails; the browser receives a visible error message instead
  4. A visible confirmation indicator appears after a successful save (input returns to static text)
**Plans**: 2 plans

Plans:
- [x] 12-01-PLAN.md — POST /save/<stem> endpoint with atomic ALTO write and XSD validation gate (TDD)
- [x] 12-02-PLAN.md — Inline word edit UX in viewer.html (single-click, Enter-to-save, green flash, error display)

### Phase 13: Upload UI and Live Progress
**Goal**: A drag-and-drop upload interface with a visible file queue, a Start button that triggers OCR, and a live progress bar fed by the SSE stream — completing the full operator workflow end-to-end
**Depends on**: Phase 9, Phase 11 (viewer linked from progress results)
**Requirements**: INGEST-01, INGEST-02, INGEST-03, PROC-01, PROC-02
**Success Criteria** (what must be TRUE):
  1. Dragging one or more TIFF files onto the upload zone adds them to a visible queue list without starting OCR
  2. Individual files can be removed from the queue before processing starts
  3. Clicking the Start button triggers OCR on all queued files; the button is disabled while processing is running
  4. A progress bar and status line update in real time showing files completed / total / percentage / ETA as OCR runs
  5. Completed files appear as clickable links in the results list and clicking one opens the side-by-side viewer for that file
**Plans**: 2 plans

Plans:
- [x] 13-01-PLAN.md — App routing: add GET /viewer/<stem>, reroute GET / to upload.html
- [x] 13-02-PLAN.md — Upload dashboard: drag zone, queue, SSE progress, results linking

### Phase 14: Viewer Zoom and Pan
**Goal**: Operators can zoom into any area of the TIFF image using the mouse wheel and pan by dragging — with the word bounding-box overlay staying pixel-accurate at all zoom levels
**Depends on**: Phase 11
**Requirements**: VIEW-05, VIEW-06
**Success Criteria** (what must be TRUE):
  1. Scrolling the mouse wheel over the TIFF image panel zooms in and out centered on the cursor position
  2. Word bounding-box overlays remain aligned with the correct word positions at every zoom level
  3. Clicking and dragging the zoomed image pans it within the panel without deselecting or triggering word clicks
  4. Zooming and panning survive a window resize without overlay misalignment (ResizeObserver continues to work)
**Plans**: 1 plan

Plans:
- [ ] 14-01-PLAN.md — Zoom/pan engine with shared-container transform, reset button, keyboard shortcuts (+/-/0), human verification

### Phase 15: VLM Article Segmentation
**Goal**: Operators can trigger automatic article segmentation for any page using a configurable VLM provider; the system identifies article regions with bounding boxes, types, titles, and section metadata stored per page
**Depends on**: Phase 12 (ALTO XML stability), Phase 10 (TIFF image endpoint)
**Requirements**: STRUCT-01, STRUCT-02, STRUCT-03
**Success Criteria** (what must be TRUE):
  1. Running segmentation with `--vlm-provider` / `--vlm-model` (or config-file equivalents) sends the page image to the configured provider and returns a response without error
  2. Detected article regions each have a bounding box, a type label (headline / article / advertisement / illustration / caption), and a title string stored in a per-page JSON file
  3. Changing the provider from one VLM (e.g., Claude Vision) to another (e.g., GPT-4o) requires only a config change with no code modification
  4. Pages with no detectable article regions produce an empty region list rather than an error
**Plans**: 2 plans

Plans:
- [ ] 15-01-PLAN.md — vlm.py provider module (Claude + OpenAI), POST/GET /segment/<stem> endpoints, CLI flags (TDD)
- [ ] 15-02-PLAN.md — Segment button in viewer.html, region overlay drawing, loadFile() restore

### Phase 16: METS/MODS Output
**Goal**: For each processed issue, the system writes a METS/MODS logical structure document with article-level div elements linked to ALTO word coordinates, conforming to the DFG Viewer / Goobi-Kitodo newspaper ingest profile
**Depends on**: Phase 15 (article metadata), Phase 12 (stable ALTO XML)
**Requirements**: STRUCT-04
**Success Criteria** (what must be TRUE):
  1. Running the METS/MODS export produces a valid XML file that passes the DFG Viewer newspaper METS profile XSD without errors
  2. Each identified article appears as a logical `<div>` element in the METS file with a type attribute and a title drawn from STRUCT-03 metadata
  3. Each article div contains `<area>` elements that reference the correct ALTO file and word-level `BEGIN`/`END` IDs from the corresponding ALTO XML
  4. Re-running the export after adding new articles to a page overwrites the METS file with updated content without corrupting existing article entries
**Plans**: 2 plans

Plans:
- [x] 16-01-PLAN.md — schemas/mets.xsd + mets.py builder + GET /mets endpoint + --issue-title CLI flag (TDD)
- [x] 16-02-PLAN.md — Download METS button on upload dashboard + human verification

### Phase 17: VLM Settings UI
**Goal**: Operators can configure the VLM provider (Open WebUI or OpenRouter) through a web settings panel on the upload dashboard, with API key and model selection persisted to disk — eliminating the need for CLI flags to enable article segmentation
**Depends on**: Phase 15 (VLM segmentation), Phase 13 (upload dashboard)
**Requirements**: STRUCT-02 (configurable provider)
**Success Criteria** (what must be TRUE):
  1. A settings panel on the upload dashboard lets the operator choose between Open WebUI and OpenRouter backends with pre-filled base URLs
  2. The operator can enter an API key and select a model from a curated list (or load live models with a button)
  3. Settings are saved to `output/settings.json` and survive server restarts — the Segment button in the viewer works without CLI flags after saving
  4. Switching backends and clicking Save immediately takes effect for subsequent segmentation requests without restarting the server
**Plans**: 2 plans

Plans:
- [x] 17-01-PLAN.md — OpenAICompatibleProvider in vlm.py + GET/POST /settings + GET /settings/models + segment_page() reads settings.json first (TDD)
- [x] 17-02-PLAN.md — Settings panel on upload dashboard: backend selector, base URL, API key, model dropdown, Save button

### Phase 18: Article Browser and Full-Text Search
**Goal**: Operators can browse identified articles for any page in a viewer sidebar and search across all articles by title or content from the web interface
**Depends on**: Phase 15 (article metadata), Phase 16 (METS/MODS output), Phase 14 (stable viewer)
**Requirements**: STRUCT-05, STRUCT-06
**Success Criteria** (what must be TRUE):
  1. Opening a file in the viewer shows a sidebar listing all identified articles for that page with their type and title
  2. Clicking an article in the sidebar highlights its bounding region on the TIFF image
  3. Typing a query into the search field returns a ranked list of matching articles with the file stem and article title visible in each result
  4. Clicking a search result opens the correct file in the viewer with the matched article's region highlighted
  5. The search index updates automatically when new segmentation results are saved so new articles appear in subsequent queries without a manual rebuild step
**Plans**: 2 plans

Plans:
- [x] 18-01-PLAN.md — search.py (SQLite FTS5: init_db, index_stem, query) + GET /articles/<stem> + GET /api/search?q= + auto-index hook in segment_page() (TDD)
- [x] 18-02-PLAN.md — Article list panel in viewer right panel + highlightRegion() + search bar on upload dashboard + search.html results page + human verification

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
| 14. Viewer Zoom and Pan | 1/1 | Complete    | 2026-03-01 | - |
| 15. VLM Article Segmentation | v1.5 | 2/2 | Complete | 2026-03-01 |
| 16. METS/MODS Output | v1.5 | 2/2 | Complete | 2026-03-01 |
| 17. VLM Settings UI | v1.5 | 2/2 | Complete | 2026-03-02 |
| 18. Article Browser and Full-Text Search | 2/2 | Complete   | 2026-03-02 | - |
