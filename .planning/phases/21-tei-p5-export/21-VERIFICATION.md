---
phase: 21-tei-p5-export
verified: 2026-03-03T13:00:00Z
status: passed
score: 18/18 must-haves verified
re_verification: false
---

# Phase 21: TEI P5 Export Verification Report

**Phase Goal:** Users can download a single TEI P5 XML file per page that encodes article structure, text with line and page markers, and facsimile coordinates — ready for scholarly use
**Verified:** 2026-03-03
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Truths drawn from the four Success Criteria in ROADMAP.md, supplemented by the must_have truths declared in the PLAN frontmatter.

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| SC1 | User triggers TEI export and receives well-formed TEI P5 XML with `<div type="article">` per VLM region with `@n` and title | VERIFIED | `export_tei()` endpoint calls `build_tei()`; test `test_single_region_produces_one_article_div` + `test_article_div_has_n_attribute` + `test_region_title_becomes_head_element` all pass |
| SC2 | TEI contains `<lb/>` at each OCR line boundary and `<pb n="N" facs="#page-N"/>` at page transitions | VERIFIED | `_build_paragraph()` emits `<lb/>` milestones; `<pb facs="#page-{stem}">` built in `build_tei()`; tests `test_lb_between_lines_not_after_last_line` + `test_pb_facs_has_hash_prefix` pass |
| SC3 | TEI contains `<facsimile>` with `<surface xml:id="page-N">` and `<zone>` elements with ALTO-derived coordinates | VERIFIED | `build_tei()` constructs surface + zone elements; tests `test_surface_uses_alto_page_dimensions_not_jpeg` + `test_zone_coordinates_in_alto_pixel_space` pass |
| SC4 | Exported TEI is well-formed XML; `facs` references in `<pb>` resolve to `xml:id` values in `<facsimile>` | VERIFIED | Smoke test confirms `pb facs="#page-scan001"` vs `surface xml:id="page-scan001"` — hash-stripped surface ID matches hash-prefixed `<pb>` reference; all 156 tests pass |
| P1 | `build_tei(output_dir, stem)` returns UTF-8 bytes beginning with XML declaration | VERIFIED | `test_returns_bytes_with_xml_declaration` passes; smoke test confirms `b"<?xml version='1.0' encoding='"` |
| P2 | Root element is `<TEI xmlns='http://www.tei-c.org/ns/1.0'>` | VERIFIED | `test_root_is_tei_element_with_tei_namespace` passes; root.tag confirmed as `{http://www.tei-c.org/ns/1.0}TEI` |
| P3 | Each VLM article region produces one `<div type="article">` with `@n` and optional `<head>` | VERIFIED | `build_tei()` lines 424-428; body loop; `test_single_region_produces_one_article_div` + `test_article_div_has_n_attribute` + `test_region_title_becomes_head_element` pass |
| P4 | `<lb/>` milestones after inter-line boundaries; no trailing `<lb/>` after last word of `<p>` | VERIFIED | `_build_paragraph()` at tei.py:186-222; `test_lb_between_lines_not_after_last_line` passes with correct mixed-content semantics |
| P5 | End-of-line hyphens rejoined; intermediate `<lb/>` suppressed | VERIFIED | `_rejoin_hyphens()` at tei.py:125-147; `test_hyphen_rejoin_suppresses_intermediate_lb` + `test_rejoined_word_text_correct` pass; "Ver-" + "Test" → "VerTest" in output |
| P6 | `<facsimile>` contains `<surface xml:id='page-{stem}'>` with ALTO page dimensions as ulx/uly/lrx/lry | VERIFIED | `build_tei()` lines 383-390; `test_facsimile_surface_has_correct_xml_id` + `test_surface_uses_alto_page_dimensions_not_jpeg` pass |
| P7 | Each VLM region maps to `<zone>` with ALTO pixel coordinates (not JPEG space) | VERIFIED | `build_tei()` lines 392-405; `test_zone_coordinates_in_alto_pixel_space` confirms 0.5*4000=2000 for lrx |
| P8 | `facs` on `<pb>` uses `#page-{stem}` (hash); `surface xml:id` has no hash | VERIFIED | `test_pb_facs_has_hash_prefix` + `test_facsimile_surface_has_correct_xml_id` pass; smoke test confirms |
| P9 | No VLM segment data: one `<div type="article">` + XML comment noting absent VLM data | VERIFIED | `build_tei()` lines 411-420; `test_no_segments_produces_single_fallback_div_with_comment` passes |
| P10 | Words column-sorted (left-to-right across columns) | VERIFIED | `_column_sort()` at tei.py:69-118; `test_two_column_layout_left_before_right` + `test_full_width_block_sorts_before_column_blocks` pass |
| E1 | GET /tei/`<stem>` triggers file download named `<stem>_tei.xml` | VERIFIED | `export_tei()` at app.py:861; `Content-Disposition: attachment; filename="{stem}_tei.xml"`; `test_returns_xml_download_when_alto_exists` passes |
| E2 | `output/tei/<stem>.xml` written to disk after endpoint called | VERIFIED | `tei_dir.mkdir(); (tei_dir / (stem + '.xml')).write_bytes(xml_bytes)` at app.py:885-887 |
| E3 | GET /tei/`<stem>` returns 404 when no ALTO exists; 400 on path traversal | VERIFIED | `test_returns_404_when_no_alto_file` + `test_returns_400_on_path_traversal` pass |
| E4 | Download TEI button in #nav-bar; disabled until file loaded; triggers `window.location = '/tei/<stem>'` | VERIFIED | `#tei-btn` at viewer.html:170; enabled in `loadFile()` at line 350; `downloadTei()` at lines 1077-1080 |

**Score:** 18/18 truths verified

### Required Artifacts

| Artifact | Min Lines | Actual Lines | Status | Key Evidence |
|----------|-----------|--------------|--------|--------------|
| `tei.py` | 150 | 437 | VERIFIED | Exports `build_tei`, `TEI_NS`; full implementation with all helper functions |
| `tests/test_tei.py` | 100 | 328 | VERIFIED | 17 tests across 6 classes; all pass |
| `app.py` (endpoint) | — | — | VERIFIED | Contains `@app.get('/tei/<stem>')` at line 861 |
| `templates/viewer.html` (button) | — | — | VERIFIED | Contains `id="tei-btn"` at line 170 |

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `tei.py build_tei()` | `output_dir/alto/<stem>.xml` | `lxml etree.parse()`, same `ALTO21_NS` as pipeline.py | WIRED | tei.py line 17: `from pipeline import ALTO21_NS`; line 245: `etree.parse(str(alto_path))` |
| `tei.py _column_sort()` | ALTO String HPOS attributes | TextBlock HPOS clustering with gap > 20% page_width | WIRED | `_column_sort()` at tei.py:69-118; used at line 313 |
| `tei.py facsimile zones` | `segments/<stem>.json bounding_box` | `bb['x'] * page_width` (ALTO pixel space) | WIRED | tei.py lines 395-398: `int(bb['x'] * page_width)` etc. |
| `templates/viewer.html #tei-btn` | `GET /tei/<currentStem>` | `window.location = '/tei/' + encodeURIComponent(currentStem)` | WIRED | viewer.html lines 1077-1080: `downloadTei()` function present |
| `app.py export_tei()` | `tei.build_tei(output_dir, stem)` | `import tei as tei_module` | WIRED | app.py line 26: `import tei as tei_module`; line 881: `xml_bytes = tei_module.build_tei(output_dir, stem)` |
| `app.py export_tei()` | `output_dir/tei/<stem>.xml` | `tei_dir.mkdir(); tei_path.write_bytes(xml_bytes)` | WIRED | app.py lines 885-887 |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TEI-01 | 21-01, 21-02 | System generates TEI P5 XML per processed page; each VLM-identified article as `<div type="article">` with `@n` and title | SATISFIED | `build_tei()` produces correct structure; 17 tests verify article div, @n, title/head; ROADMAP goal says "per issue" but Success Criteria and PLAN must_haves consistently scope to per-page — implementation matches SC contract |
| TEI-02 | 21-01, 21-02 | TEI preserves line structure via `<lb/>` and page transitions via `<pb n="N" facs="#page-N"/>` | SATISFIED | `_build_paragraph()` emits `<lb/>`; `<pb facs="#page-{stem}">` built in `build_tei()`; tests confirm correct behavior |
| TEI-03 | 21-01, 21-02 | TEI includes `<facsimile>` with `<surface xml:id="page-N">` and `<zone>` elements with ALTO-derived coordinates | SATISFIED | `build_tei()` lines 382-405; tests confirm ALTO pixel coords used (not JPEG space) |

**Notes on requirement alignment:**

The REQUIREMENTS.md text for TEI-01 says "per processed issue combining all pages". The ROADMAP.md Goal says "per issue". However the ROADMAP.md Success Criteria for Phase 21 (which take precedence per verification process) describe single-page behavior. The PLAN must_haves, implementation, and all tests are consistently scoped to per-page. The user-verified checkpoint in Plan 02 (Task 3) was approved against this per-page scope. The discrepancy is a documentation artifact in REQUIREMENTS.md/ROADMAP Goal text — the implemented scope is per-page, consistent with the SC contract, and the human checkpoint was approved.

**Orphaned requirements (TEI-04, TEI-05):** These appear in REQUIREMENTS.md under "Possible v1.7+" and are NOT mapped to Phase 21 in the traceability table — not orphaned for this phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tei.py` | 271-275 | `string_to_block` loop computes unused `key` tuple but keys dict by `str(id(s))` — comment says id() is unsafe but code uses it anyway | Info | No functional impact: `all_strings` materialized before this loop so proxy ids are stable; 17 tests pass confirming correctness |

No blockers. No warnings. One informational code quality note.

### Human Verification Required

The Plan 02 Task 3 checkpoint was a `gate="blocking"` human-verify task. Per 21-02-SUMMARY.md, the user approved this checkpoint. The following items were covered by that approval and cannot be re-verified programmatically:

**1. Browser Download Behavior**
**Test:** Load a page in the viewer, click "Download TEI"
**Expected:** Browser prompts to save `<stem>_tei.xml`; file opens as well-formed TEI P5 XML
**Why human:** Browser file download behavior cannot be automated in Flask test client
**Status:** Approved by user during Task 3 checkpoint (2026-03-03)

**2. Button Visual State**
**Test:** Observe "Download TEI" button before and after loading a page
**Expected:** Green button, disabled (grey) on initial load, enabled after a file loads
**Why human:** Visual CSS state cannot be verified programmatically
**Status:** Approved by user during Task 3 checkpoint (2026-03-03)

**3. Disk File Written After Download**
**Test:** After clicking Download TEI, check `output/tei/<stem>.xml` on disk
**Expected:** File exists and contains valid TEI P5 XML
**Why human:** Requires live Flask server run
**Status:** Code path verified (`tei_dir.mkdir(); tei_path.write_bytes(xml_bytes)` at app.py:885-887); approved at checkpoint

### Test Suite Results

```
tests/test_tei.py      17 passed (all 6 classes: Namespace, Facsimile, Body, LineBreaks, ColumnSort, Idempotent)
tests/test_app.py      3 passed  (TestExportTei: success download, 404, 400)
Full suite             156 passed (no regressions from 153 pre-phase baseline)
```

### Gaps Summary

No gaps. All 18 observable truths verified, all 4 required artifacts exist and are substantive, all 6 key links confirmed wired, all 3 requirements satisfied, no anti-pattern blockers, human checkpoint approved.

---

_Verified: 2026-03-03T13:00:00Z_
_Verifier: Claude (gsd-verifier)_
