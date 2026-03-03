---
phase: 21-tei-p5-export
plan: 01
subsystem: api
tags: [tei, lxml, xml, alto, vlm, column-sort, hyphen-rejoin]

requires:
  - phase: 19-text-normalization
    provides: line_end flag and lxml proxy recycling fix pattern (materialise root.iter() once)
  - phase: 20-structure-detection
    provides: VLM segment JSON with bounding_box, bb.x * page_width coordinate conversion
  - phase: 16-mets-mods-output
    provides: ALTO21_NS constant, mets.py structure mirror pattern

provides:
  - tei.py module with build_tei(output_dir, stem) -> bytes
  - TEI_NS constant exported at module level
  - _column_sort(), _rejoin_hyphens(), _build_paragraph() private helpers
  - tests/test_tei.py: 17 tests across 6 classes (all green)

affects: [21-02 (Flask endpoint wrapping build_tei)]

tech-stack:
  added: []
  patterns:
    - "TEI P5 XML builder mirrors mets.py: single build_* function, lxml Clark notation, etree.tostring with xml_declaration"
    - "Column sort: TextBlock HPOS clustering with gap > 20% page_width; full-width blocks (> 60%) sort first"
    - "Hyphen rejoin: walk words, if content ends '-' and line_end=True merge with next word, inherit next word's line_end"
    - "Mixed content <lb/>: flush pending text to p.text or last child tail, add lb with empty tail, reset pending"
    - "lxml proxy recycling: string_to_block built by id(s) during same iteration as all_blocks; all_strings materialised once before word loop"

key-files:
  created:
    - tei.py
    - tests/test_tei.py
  modified: []

key-decisions:
  - "ALTO fixture revised: 'Ver-' in its own TextLine so line_end=True enables hyphen rejoin test"
  - "lb-at-end test: checks empty .tail on trailing lb (correct mixed-content semantics) rather than presence of lb as last child"
  - "facs on <surface>: ../uploads/{stem}.tif (matches app.py UPLOAD_SUBDIR pattern from RESEARCH)"
  - "No VLM fallback: pb placed inside fallback div (not body) for consistent structure"

patterns-established:
  - "Pattern: TEI mixed content — lb.tail carries next-line text; last word flushed to p.text or last-lb.tail with no trailing empty lb"
  - "Pattern: column sort key tuple (column_index, block_vpos, word_vpos, word_hpos) — stable across reruns"

requirements-completed: [TEI-01, TEI-02, TEI-03]

duration: 22min
completed: 2026-03-03
---

# Phase 21 Plan 01: TEI P5 XML Builder Summary

**tei.py module with build_tei() implementing column-sorted, hyphen-rejoined TEI P5 XML from ALTO 2.1 and VLM segment JSON, verified by 17-test TDD suite**

## Performance

- **Duration:** 22 min
- **Started:** 2026-03-03T12:03:26Z
- **Completed:** 2026-03-03T12:25:46Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 2

## Accomplishments

- tei.py module with build_tei(output_dir, stem) -> UTF-8 bytes, TEI_NS exported
- _column_sort(): groups TextBlocks by HPOS gap > 20% page_width; full-width blocks (> 60%) sort first with column_index = -1
- _rejoin_hyphens(): merges "Ver-" + next-word → "VerTest", line_end inherited from consumed word, intermediate lb suppressed
- _build_paragraph(): inter-line <lb/> milestones with pending-text flush pattern; no trailing empty lb
- facsimile <surface xml:id="page-{stem}"> (no hash) + <zone> in ALTO pixel coords (bb * page_width/height)
- <pb facs="#page-{stem}"> fragment reference (with hash)
- No VLM fallback: single <div type="article"> + body XML comment
- 153 tests green (136 existing + 17 new — no regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — write failing tests for tei.py** - `baebb6c` (test)
2. **Task 2: GREEN — implement tei.py to pass all tests** - `bf624cb` (feat)

## Files Created/Modified

- `/Users/zu54tav/Zeitschriften-OCR/tei.py` — TEI P5 XML builder module, 250 lines
- `/Users/zu54tav/Zeitschriften-OCR/tests/test_tei.py` — 17-test suite across 6 classes, 330 lines

## Decisions Made

- **ALTO fixture redesign:** The plan described "Ver-" as a "line_end candidate" in a two-word TextLine alongside "Test". For `line_end=True` to fire on "Ver-", it must be the SOLE word in its TextLine. Revised fixture to three lines in Block 0: line_0 (Hello/World), line_1 (Ver- only), line_2 (Test only). This makes hyphen rejoin semantics unambiguous and correctly produces "VerTest".

- **lb assertion semantics:** Original test checked `last_child.tag != lb` for all `<p>` elements. In lxml mixed content, `<lb/>` between two lines has the second line's text in its `.tail` — so the lb IS the last element child when the second line is the final line. Revised assertion: allow lb as last child only if `.tail.strip()` is non-empty (text follows on next line). Empty tail lb = forbidden trailing marker.

- **facs on surface:** Used `../uploads/{stem}.tif` per RESEARCH recommendation (CONTEXT.md `../scans/` example was illustrative; uploads go to `output/uploads/` per app.py UPLOAD_SUBDIR).

- **pb placement in no-VLM fallback:** Placed `<pb>` inside the fallback `<div type="article">` so structure is consistent; in the segmented path `<pb>` is a direct child of `<body>`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ALTO fixture had "Ver-" as non-line-terminal word — hyphen rejoin impossible**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** Plan fixture had "Ver-" and "Test" in the same TextLine; only the last String in a TextLine gets `line_end=True`, so "Test" was line_end, not "Ver-". Hyphen rejoin requires the hyphenated word to be line_end=True.
- **Fix:** Revised ALTO_FIXTURE to put "Ver-" alone in line_1 (line_end=True) and "Test" alone in line_2 (continuation). Also updated the test comment header to document the new structure.
- **Files modified:** tests/test_tei.py
- **Verification:** `test_hyphen_rejoin_suppresses_intermediate_lb` and `test_rejoined_word_text_correct` pass
- **Committed in:** bf624cb (Task 2 commit)

**2. [Rule 1 - Bug] lb-at-end assertion was too strict for correct TEI mixed-content**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** Test checked `list(p)[-1].tag != lb` but in correct TEI mixed content `<lb/>` IS the last child element when the final line's text is in its `.tail`. This rejects valid `Right Column<lb/>End` structure.
- **Fix:** Changed assertion to: if last child is lb, require non-empty `.tail` (text must follow). Empty tail lb = trailing marker = forbidden.
- **Files modified:** tests/test_tei.py
- **Verification:** `test_lb_between_lines_not_after_last_line` passes with correct semantics
- **Committed in:** bf624cb (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - test fixture/assertion bugs discovered during GREEN phase)
**Impact on plan:** Both fixes were necessary to correctly test the specification. Implementation logic was correct; tests needed alignment with TEI mixed-content model.

## Issues Encountered

None beyond the two Rule 1 auto-fixes documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- tei.py module ready for import by Plan 02 Flask endpoint
- build_tei(output_dir, stem) contract confirmed by 17 tests
- TEI_NS, build_tei exported for `import tei as tei_module` in app.py
- Plan 02: add GET /tei/<stem> endpoint, write to output/tei/<stem>.xml, serve as attachment, add "Download TEI" button

---
*Phase: 21-tei-p5-export*
*Completed: 2026-03-03*
