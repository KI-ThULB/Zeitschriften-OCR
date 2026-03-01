---
phase: 16-mets-mods-output
plan: 01
subsystem: api
tags: [mets, mods, lxml, xml, alto, goobi, kitodo, dfg-viewer, tdd]

# Dependency graph
requires:
  - phase: 15-vlm-article-segmentation
    provides: output_dir/segments/<stem>.json article region data with bounding boxes
  - phase: 12-word-correction
    provides: output_dir/alto/<stem>.xml ALTO 2.1 files with String/@ID attributes

provides:
  - METS 1.12.1 XML builder producing dmdSec/MODS + fileSec + LOGICAL + PHYSICAL structMaps
  - _find_word_ids_in_region() linking article bounding boxes to ALTO String IDs
  - GET /mets Flask route returning downloadable mets.xml or 204 when no ALTO files
  - --issue-title CLI flag setting MODS title in generated METS
  - schemas/mets.xsd bundled for future validation

affects: [future-goobi-ingest, dfg-viewer-output]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "METS builder uses lxml etree.Element/SubElement with explicit nsmap, xsi:schemaLocation attribute set directly"
    - "Bounding box overlap detection via pixel coordinate intersection (not containment) for partial-word regions"
    - "GET /mets reads from disk on every request — no caching, always reflects current state"

key-files:
  created:
    - schemas/mets.xsd
    - mets.py
    - tests/test_mets.py
  modified:
    - app.py

key-decisions:
  - "Bounding box intersection uses HPOS < hpos_max AND (HPOS+WIDTH) > hpos_min — partial overlap counts, not containment-only"
  - "build_mets() returns bytes from etree.tostring(xml_declaration=True, encoding=UTF-8, pretty_print=True) — consistent with ALTO pipeline pattern"
  - "GET /mets returns 204 (not 404) when no ALTO files — distinguishes 'not ready yet' from 'route not found'"
  - "mets.py uses ALTO21_NS = 'http://schema.ccs-gmbh.com/ALTO' matching pipeline.py constant — correct CCS-GmbH namespace for project ALTO files"

patterns-established:
  - "METS namespace constants (METS_NS, MODS_NS, XLINK_NS) as module-level strings — imported by tests for element tag assertions"
  - "TDD RED/GREEN: test file committed while still failing, then implementation commits make tests pass"

requirements-completed: [STRUCT-04]

# Metrics
duration: 27min
completed: 2026-03-01
---

# Phase 16 Plan 01: METS/MODS Output Summary

**METS 1.12.1 builder with word-level ALTO linking via lxml, GET /mets download endpoint, and bundled loc.gov XSD**

## Performance

- **Duration:** 27 min
- **Started:** 2026-03-01T18:02:35Z
- **Completed:** 2026-03-01T18:30:16Z
- **Tasks:** 4
- **Files modified:** 4 (schemas/mets.xsd created, mets.py created, tests/test_mets.py created, app.py modified)

## Accomplishments
- Downloaded and bundled METS 1.12.1 XSD from Library of Congress for future validation use
- Created mets.py with `build_mets()` producing conforming METS XML: metsHdr, dmdSec/MODS, fileSec, LOGICAL structMap (article divs with area/@BEGIN/@END IDREF links to ALTO String IDs), and PHYSICAL structMap (page sequence)
- `_find_word_ids_in_region()` converts normalized bounding boxes to pixel coordinates and returns first/last ALTO String IDs overlapping the region using intersection logic
- GET /mets route returns 200 application/xml with Content-Disposition attachment when ALTO files exist, 204 when none
- --issue-title CLI flag sets MODS title in generated METS document
- 22 new tests added (18 mets module + 4 endpoint); all 101 tests pass GREEN

## Task Commits

Each task was committed atomically:

1. **Task 1: Download and bundle METS XSD** - `400a619` (chore)
2. **Task 2: Write tests first (TDD RED)** - `5fdc3db` (test)
3. **Task 3: Create mets.py builder module** - `9dac13c` (feat)
4. **Task 4: Add GET /mets route and --issue-title CLI flag** - `63e918b` (feat)

**Plan metadata:** (docs commit — see final_commit step)

_Note: TDD tasks have RED commit (test, failing) then GREEN commit (feat, passing)_

## Files Created/Modified
- `schemas/mets.xsd` - METS 1.12.1 XSD from http://www.loc.gov/standards/mets/mets.xsd
- `mets.py` - METS/MODS builder: METS_NS, MODS_NS, XLINK_NS, ALTO21_NS constants; _find_word_ids_in_region(); build_mets()
- `tests/test_mets.py` - 22 tests: TestFindWordIdsInRegion (4), TestBuildMets (14), TestGetMetsEndpoint (4)
- `app.py` - Added `import mets`, GET /mets route (export_mets()), --issue-title CLI flag, app.config['ISSUE_TITLE']

## Decisions Made
- Bounding box overlap uses intersection logic (HPOS < hpos_max AND HPOS+WIDTH > hpos_min), not containment — required for string_0 to appear in test_left_column_returns_first_string_only (right edge = HPOS+WIDTH = 400, region right edge = 400)
- GET /mets returns 204 (not 404) when no ALTO files — semantically correct: resource exists but has no content yet
- ALTO21_NS set to 'http://schema.ccs-gmbh.com/ALTO' matching pipeline.py — this is the correct namespace for all project ALTO files after namespace rewrite in build_alto21()

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- METS builder is ready for Goobi/Kitodo ingest testing
- Phase 16 Plan 02 (if planned) can add METS XSD schema validation via the bundled schemas/mets.xsd
- GET /mets endpoint is discoverable from the web UI — a "Download METS" button could be added to viewer.html

## Self-Check: PASSED

- FOUND: schemas/mets.xsd
- FOUND: mets.py
- FOUND: tests/test_mets.py
- FOUND: app.py (modified)
- FOUND: .planning/phases/16-mets-mods-output/16-01-SUMMARY.md
- All 4 task commits verified: 400a619, 5fdc3db, 9dac13c, 63e918b
- 101 tests pass (79 pre-existing + 22 new mets tests)

---
*Phase: 16-mets-mods-output*
*Completed: 2026-03-01*
