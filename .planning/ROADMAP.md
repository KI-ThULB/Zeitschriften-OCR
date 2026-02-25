# Roadmap: Zeitschriften-OCR

## Milestones

- ✅ **v1.0 Single-File Pipeline** — Phase 1 (shipped 2026-02-24)
- ✅ **v1.1 Batch Processor** — Phases 2–3 (shipped 2026-02-25)
- 🚧 **v1.2 Image Preprocessing** — Phases 4–5 (in progress)

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

### 🚧 v1.2 Image Preprocessing (In Progress)

**Milestone Goal:** Improve OCR accuracy on imperfect archival scans by adding deskew correction and adaptive thresholding as preprocessing steps before OCR.

- [x] **Phase 4: Deskew** — Detect and correct scan rotation before OCR, with per-file angle logging and safe fallback (completed 2026-02-25)
- [ ] **Phase 5: Adaptive Thresholding** — Add opt-in Gaussian adaptive binarization for scans with uneven illumination

## Phase Details

### Phase 4: Deskew
**Goal**: Every TIFF is automatically rotated to upright orientation before OCR, with the correction angle visible in run output and graceful handling of detection failures
**Depends on**: Phase 3
**Requirements**: PREP-01, PREP-02, PREP-03
**Success Criteria** (what must be TRUE):
  1. Running a batch produces upright OCR input for each TIFF — no manual pre-rotation needed
  2. Each per-file result line reports the detected angle (e.g. `[deskew: 1.4°]`) so the operator can see what was corrected
  3. When deskew fails or produces an implausible angle, the file is processed using its original orientation and a warning appears in the output — the batch does not abort
  4. A zero-degree (no rotation needed) scan passes through without any quality degradation or extra processing artifacts
**Plans**: 1 plan

Plans:
- [ ] 04-01-PLAN.md — Add deskew_image() function and wire into process_tiff() with angle reporting

### Phase 5: Adaptive Thresholding
**Goal**: Scans with uneven illumination can be binarized using adaptive Gaussian thresholding when the operator opts in, without affecting the default pipeline behavior
**Depends on**: Phase 4
**Requirements**: PREP-04, PREP-05
**Success Criteria** (what must be TRUE):
  1. Running a batch without `--adaptive-threshold` produces identical output to a pre-v1.2 run — no behavioral change by default
  2. Running with `--adaptive-threshold` applies Gaussian block-based thresholding to each scan before OCR and produces valid ALTO 2.1 output
  3. The `--help` output lists `--adaptive-threshold` with a description, confirming it is a discoverable CLI flag
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Single-File Pipeline | v1.0 | 2/2 | Complete | 2026-02-24 |
| 2. Batch Orchestration and CLI | v1.1 | 2/2 | Complete | 2026-02-24 |
| 3. Validation and Reporting | v1.1 | 2/2 | Complete | 2026-02-25 |
| 4. Deskew | 1/1 | Complete    | 2026-02-25 | - |
| 5. Adaptive Thresholding | v1.2 | 0/? | Not started | - |
