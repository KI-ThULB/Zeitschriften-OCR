# Roadmap: Zeitschriften-OCR

## Milestones

- ✅ **v1.0 Single-File Pipeline** — Phase 1 (shipped 2026-02-24)
- ✅ **v1.1 Batch Processor** — Phases 2–3 (shipped 2026-02-25)
- ✅ **v1.2 Image Preprocessing** — Phases 4–5 (shipped 2026-02-25)
- 🚧 **v1.3 Operator Experience** — Phases 6–8 (in progress)

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

### 🚧 v1.3 Operator Experience (In Progress)

**Milestone Goal:** Make long batch runs observable and configurable — progress visibility, dry-run preview, verbose diagnostics, and JSON config file support.

- [ ] **Phase 6: Diagnostic Flags** — Dry-run preview and verbose per-file timing without changing pipeline contract
- [ ] **Phase 7: Live Progress Display** — Real-time progress line (count / percentage / ETA) updated as each file completes
- [ ] **Phase 8: Config File Support** — JSON config file loading with CLI override and robust error handling

## Phase Details

### Phase 6: Diagnostic Flags
**Goal**: Operators can inspect what the pipeline will do and how it performs without reading source code
**Depends on**: Phase 5
**Requirements**: OPER-01, OPER-02
**Success Criteria** (what must be TRUE):
  1. Running with `--dry-run` prints every TIFF that would be processed and every TIFF that would be skipped, then exits with code 0 and no OCR output files written
  2. Running with `--verbose` prints Tesseract stdout/stderr for each processed file to the terminal
  3. Running with `--verbose` prints four wall-clock timing lines per file: deskew, crop, OCR, and write stage durations
  4. `--dry-run` and `--verbose` can be combined with all existing flags (`--force`, `--lang`, `--workers`, etc.) without error
**Plans**: TBD

### Phase 7: Live Progress Display
**Goal**: Operators running large batches can see how far along the job is and estimate when it will finish
**Depends on**: Phase 6
**Requirements**: OPER-03
**Success Criteria** (what must be TRUE):
  1. During batch processing a single line is updated in-place each time a file completes, showing files-done / total-files / percentage
  2. The progress line shows an estimated time remaining that updates as each file completes
  3. The final progress line is cleared or resolved cleanly before the Done summary line is printed
**Plans**: TBD

### Phase 8: Config File Support
**Goal**: Operators can persist flag defaults in a JSON file so repeated invocations don't require long command lines
**Depends on**: Phase 7
**Requirements**: OPER-04, OPER-05
**Success Criteria** (what must be TRUE):
  1. Passing `--config config.json` with a valid JSON file sets flag defaults; any flag also specified on the command line silently takes precedence
  2. Passing `--config missing.json` (file does not exist) prints a clear error message and exits before any TIFF is read or processed
  3. Passing `--config bad.json` (file exists but contains invalid JSON) prints a clear error message and exits before any TIFF is read or processed
  4. Omitting `--config` entirely leaves all existing default values unchanged; no backward-compatibility break
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Single-File Pipeline | v1.0 | 2/2 | Complete | 2026-02-24 |
| 2. Batch Orchestration and CLI | v1.1 | 2/2 | Complete | 2026-02-24 |
| 3. Validation and Reporting | v1.1 | 2/2 | Complete | 2026-02-25 |
| 4. Deskew | v1.2 | 1/1 | Complete | 2026-02-25 |
| 5. Adaptive Thresholding | v1.2 | 1/1 | Complete | 2026-02-25 |
| 6. Diagnostic Flags | v1.3 | 0/TBD | Not started | - |
| 7. Live Progress Display | v1.3 | 0/TBD | Not started | - |
| 8. Config File Support | v1.3 | 0/TBD | Not started | - |
