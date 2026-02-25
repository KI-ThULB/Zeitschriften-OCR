# Requirements: Zeitschriften-OCR

**Defined:** 2026-02-25
**Core Value:** Every TIFF in the input folder gets a correctly structured ALTO 2.1 XML file, produced without manual intervention and with safe reruns.

## v1.3 Requirements

### Operator Experience

- [ ] **OPER-01**: `--dry-run` flag lists every TIFF that would be processed and every TIFF that would be skipped (already has ALTO output), then exits without running OCR
- [ ] **OPER-02**: `--verbose` flag prints Tesseract stdout/stderr and per-stage wall-clock timing (deskew, crop, OCR, write) for each processed file
- [ ] **OPER-03**: During batch processing, a live progress line shows files completed, total count, percentage, and estimated time remaining (updated as each file completes)
- [ ] **OPER-04**: `--config PATH` loads CLI flag defaults from a JSON file; any flag specified on the command line overrides the config value
- [ ] **OPER-05**: If `--config PATH` is specified but the file does not exist or is not valid JSON, pipeline exits with a clear error message before any processing begins

## Future Requirements

### Operator Experience

- **OPER-06**: Dry run mode (`--dry-run`) — machine-readable output (JSON) for scripting integration

### Output Formats

- **OUTP-01**: ALTO 3.x / 4.x output option (`--alto-version`) for systems requiring newer schemas

### Integration

- **INTG-01**: Goobi/Kitodo plugin packaging — wrap CLI as a Goobi script step plugin

## Out of Scope

| Feature | Reason |
|---------|--------|
| GUI or web interface | CLI batch tool only |
| PDF input | Input is TIFF only per project spec |
| Multi-language OCR per run | Single language per run; `--lang` flag covers edge cases |
| Cloud or distributed processing | Local CLI tool |
| Saving preprocessed images as deliverables | Preprocessing is intermediate only; originals stay untouched |
| Image quality scoring | Out of scope; quality judged by downstream Goobi operator review |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OPER-01 | Phase 6 | Pending |
| OPER-02 | Phase 6 | Pending |
| OPER-03 | Phase 7 | Pending |
| OPER-04 | Phase 8 | Pending |
| OPER-05 | Phase 8 | Pending |

**Coverage:**
- v1.3 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-25*
