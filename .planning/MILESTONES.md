# Milestones

## v1.0 Single-File Pipeline (Shipped: 2026-02-24)

**Phases completed:** 1 phase, 2 plans, 4 tasks

**Stats:**
- Timeline: 2026-02-24 (~5 hours)
- Files: 5 changed, 449 insertions
- LOC: 308 lines Python (pipeline.py) + requirements.txt
- Git range: `24a10a4` (requirements.txt) → `fedd094` (process_tiff/main)

**Key accomplishments:**
- Pillow-based TIFF loader with DPI extraction and (300.0, 300.0) fallback warning accumulation pattern
- OpenCV THRESH_BINARY + THRESH_OTSU contour crop with ratio-based fallback guard (40–98%) and configurable padding
- pytesseract.image_to_alto_xml piped with `--psm` and `--dpi` config flags for Tesseract LSTM engine
- ALTO 3.x → ALTO 2.1 namespace rewrite (CCS-GmbH) with crop HPOS/VPOS offset applied before namespace replace
- End-to-end verified on real 71MB Zeitschriften scan: 46 words, correct namespace, exit code 0

**Known Gaps:**
- `build_alto21()` Step 5 (`xsi:schemaLocation` removal) silently no-ops: the strip target is already mutated by Step 4's namespace replace. Output retains contradictory `xsi:schemaLocation` pointing to ALTO 3.0 XSD. Fix: `root.attrib.pop('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', None)` after Step 1.

**Archive:** `.planning/milestones/v1.0-ROADMAP.md`, `.planning/milestones/v1.0-REQUIREMENTS.md`

---

## v1.1 Batch Processor (Shipped: 2026-02-25)

**Phases completed:** 2 phases (2–3), 4 plans

**Stats:**
- Timeline: 2026-02-24 → 2026-02-25 (2 days)
- LOC: 750 lines Python (pipeline.py), +442 lines from v1.0
- Git range: `fix(02-01)` (`1b7a273`) → `docs(phase-03)` (`5596e44`)

**Key accomplishments:**
- Fixed critical ProcessPoolExecutor worker bug (`sys.exit` → `raise`) and v1.0 `xsi:schemaLocation` stripping gap
- Parallel batch OCR with `ProcessPoolExecutor`, skip-if-exists idempotency, and per-file error isolation via JSONL log
- Full CLI surface (`--input`, `--output`, `--workers`, `--force`, `--lang`, `--padding`, `--psm`) with Tesseract startup validation
- Bundled namespace-adapted ALTO 2.1 XSD (`schemas/alto-2-1.xsd`, CCS-GmbH namespace) — no network required at runtime
- Per-file ALTO coordinate sanity check (HPOS+WIDTH > page_width flagged as `validation_warnings`)
- JSON per-run summary report (`report_TIMESTAMP.json`) with `--validate-only` flag for operator re-validation

**Archive:** `.planning/milestones/v1.1-ROADMAP.md`, `.planning/milestones/v1.1-REQUIREMENTS.md`

---


## v1.2 Image Preprocessing (Shipped: 2026-02-25)

**Phases completed:** 5 phases, 8 plans, 0 tasks

**Key accomplishments:**
- (none recorded)

---


## v1.3 Operator Experience (Shipped: 2026-02-26)

**Phases completed:** 6 phases, 11 plans, 0 tasks

**Key accomplishments:**
- (none recorded)

---

