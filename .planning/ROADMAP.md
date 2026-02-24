# Roadmap: Zeitschriften-OCR

## Overview

Three phases, each building on the correctness of the last. Phase 1 gets the single-file pipeline right — DPI extraction, border crop, OCR, and ALTO 2.1 output with correct namespace and coordinate offsets. Only once a single TIFF produces a valid, display-correct ALTO file does Phase 2 add parallelism, skip logic, error isolation, and the full CLI surface. Phase 3 closes the loop with schema validation, coordinate sanity checks, and per-run reporting — providing confidence the entire batch output is correct before ingest into Goobi/Kitodo.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Single-File Pipeline** - Process one TIFF to a schema-valid ALTO 2.1 file with correct coordinates
- [ ] **Phase 2: Batch Orchestration and CLI** - Process a full folder in parallel with skip logic, error isolation, and full CLI
- [ ] **Phase 3: Validation and Reporting** - Validate all output and produce per-run summary reports

## Phase Details

### Phase 1: Single-File Pipeline
**Goal**: A single TIFF can be processed to a schema-valid ALTO 2.1 file with correct DPI, correct namespace, and word coordinates that align with the original uncropped TIFF
**Depends on**: Nothing (first phase)
**Requirements**: PIPE-01, PIPE-02, PIPE-03, PIPE-04
**Success Criteria** (what must be TRUE):
  1. Running the tool on a single TIFF produces an ALTO 2.1 XML file in the output directory
  2. The ALTO XML uses the correct namespace `xmlns="http://schema.ccs-gmbh.com/ALTO"` (not Tesseract's ALTO 3.x default)
  3. Word bounding boxes in the ALTO file are offset by the crop box, so highlights align with the original TIFF when viewed in the DFG Viewer
  4. DPI is extracted from TIFF metadata and used; if absent, a 300 DPI fallback is logged as a warning
  5. If crop detection produces a result outside 40%–98% of the original area, the pipeline falls back to original bounds and logs the fallback
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — requirements.txt + pipeline.py skeleton: load_tiff() and detect_crop_box()
- [ ] 01-02-PLAN.md — Complete pipeline.py: run_ocr(), build_alto21(), process_tiff(), main() wiring

### Phase 2: Batch Orchestration and CLI
**Goal**: The tool processes a full folder of TIFFs in parallel, skips already-processed files on rerun, isolates per-file errors, and exposes a complete CLI surface
**Depends on**: Phase 1
**Requirements**: BATC-01, BATC-02, BATC-03, BATC-04, CLI-01, CLI-02, CLI-03, CLI-04, CLI-05
**Success Criteria** (what must be TRUE):
  1. Running `python pipeline.py --input DIR --output DIR` processes all TIFFs in the input folder and writes ALTO XML to the output folder
  2. Rerunning the same command skips TIFFs that already have ALTO XML output; passing `--force` reprocesses them
  3. A TIFF that raises an error during processing does not abort the batch — remaining files continue and complete
  4. A run error log is written recording each failed file's path, exception type, error message, and stack trace
  5. At startup, the tool validates that Tesseract is installed and the requested language pack is available, exiting with a clear error message if either is missing
**Plans**: TBD

### Phase 3: Validation and Reporting
**Goal**: Every ALTO output file is validated against the ALTO 2.1 XSD schema and a per-run JSON summary report is written, giving the operator confidence in the batch before Goobi ingest
**Depends on**: Phase 2
**Requirements**: VALD-01, VALD-02, VALD-03
**Success Criteria** (what must be TRUE):
  1. Each ALTO output file is validated against the ALTO 2.1 XSD schema; violations are logged per file without aborting the batch
  2. Each ALTO file is checked for word bounding boxes that exceed the page dimensions; violations are logged per file without aborting
  3. After a batch run, a JSON summary report exists containing for each file: input path, output path, processing duration, word count, and error status
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Single-File Pipeline | 0/2 | Planned | - |
| 2. Batch Orchestration and CLI | 0/? | Not started | - |
| 3. Validation and Reporting | 0/? | Not started | - |
