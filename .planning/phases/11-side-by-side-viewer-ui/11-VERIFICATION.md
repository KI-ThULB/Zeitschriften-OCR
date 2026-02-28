---
phase: 11-side-by-side-viewer-ui
verified: 2026-02-28T12:00:00Z
status: human_needed
score: 9/9 automated must-haves verified
re_verification: false
human_verification:
  - test: "SVG bounding box alignment on a real document"
    expected: "Clicking a word in the text panel draws a yellow/orange-stroke SVG rect that visually aligns with that word's position in the TIFF image"
    why_human: "Scale-factor computation (img.clientWidth / pageWidth) is correct in code but only visible accuracy can be confirmed with a real ALTO file rendered in a browser"
  - test: "ResizeObserver repositions rect on window resize"
    expected: "After dragging the browser window to a new size the SVG rect stays aligned with the same word without shifting"
    why_human: "ResizeObserver is browser-only; pytest cannot exercise it"
  - test: "Bidirectional click: SVG rect -> text panel scroll"
    expected: "Clicking the highlighted yellow rect causes the text panel to scroll so the corresponding word span is in view and gains the 'selected' CSS class (bold + yellow background)"
    why_human: "scrollIntoView and DOM scroll behavior are browser-only"
  - test: "Left/Right arrow key navigation with INPUT guard"
    expected: "Pressing Left/Right arrow keys navigates between files; navigation is suppressed when an INPUT element has focus"
    why_human: "Keyboard event dispatch and focus state require a browser"
  - test: "Previous/Next button disabled state at boundaries"
    expected: "Prev button is visually disabled (opacity 0.4) at the first file; Next button is visually disabled at the last file"
    why_human: "Visual disabled rendering requires browser rendering"
---

# Phase 11: Side-by-Side Viewer UI Verification Report

**Phase Goal:** A two-panel viewer page showing the TIFF image on the left and OCR word text on the right, with SVG bounding box overlays and bidirectional click cross-reference between text and image
**Verified:** 2026-02-28T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| 1  | GET /files returns 200 JSON with a 'stems' key containing an alphabetically sorted list of stems from alto/*.xml | VERIFIED | `list_files()` at app.py:484 uses `alto_dir.glob('*.xml')` + `sorted()`; TestFilesEndpoint::test_returns_sorted_stems passes |
| 2  | GET /files returns {'stems': []} when alto/ directory does not exist | VERIFIED | Early-return at app.py:488-489 when `not alto_dir.exists()`; TestFilesEndpoint::test_returns_empty_when_no_alto_dir passes |
| 3  | GET / returns 200 with content-type text/html (viewer entry point) | VERIFIED | `viewer()` at app.py:495-497 calls `render_template('viewer.html')`; TestViewerRoute::test_viewer_returns_200_html passes |
| 4  | The sidebar lists all stems from GET /files; clicking a stem loads that file without a full page reload | VERIFIED | viewer.html:70-74 fetches '/files' on DOMContentLoaded, calls `renderSidebar(stems)` which injects `.file-item` divs; `loadFile()` is called on click without page reload |
| 5  | The left panel shows the TIFF JPEG; the right panel shows every OCR word as an inline clickable span | VERIFIED | viewer.html:109 sets `img.src = '/image/${stem}'`; viewer.html:112 fetches `/alto/${stem}`, calls `renderWords(data.words)` which injects `<span class="word">` elements |
| 6  | Clicking a word span draws a semi-transparent yellow + orange stroke SVG rect over the corresponding ALTO bounding box on the image | VERIFIED (browser needed for visual accuracy) | `selectWord()` at viewer.html:142-154 calls `showHighlight(word)` which sets SVG rect attributes using `img.clientWidth / pageWidth` scale; fill is `rgba(255,220,0,0.35)`, stroke is `orange`; pointer-events set to `all` when visible |
| 7  | Clicking the SVG rect scrolls the text panel to highlight the corresponding word span | VERIFIED (browser needed for scroll behavior) | viewer.html:57-64 attaches click listener to `#highlight-rect`; uses `rect.dataset.wordId` to find matching `.word[data-id]` span and calls `scrollIntoView()` |
| 8  | Bounding box position updates correctly when the browser window is resized (ResizeObserver recomputes scale factors) | VERIFIED (browser needed for observable effect) | `setupResizeObserver()` at viewer.html:176-183 attaches `ResizeObserver` to `#tiff-img`; callback calls `showHighlight(activeWord)` if `activeWord !== null` and `img.clientWidth !== 0` |
| 9  | Previous/Next buttons above the panels navigate to adjacent files; Prev disabled at index 0, Next disabled at last index | VERIFIED (browser needed for visual confirmation) | viewer.html:28-29 start both buttons `disabled`; viewer.html:99-100 update `disabled` state in `loadFile()`; `setupNavButtons()` at viewer.html:185-188 wires click listeners to `navigateTo()` |
| 10 | Left/Right arrow keys navigate prev/next; navigation suppressed when focus is inside an INPUT element | VERIFIED (browser needed for interactive confirmation) | `setupKeyboard()` at viewer.html:194-199 guards on `document.activeElement.tagName === 'INPUT'` before calling `navigateTo()` |
| 11 | On file change, both panels scroll to top and the SVG highlight is cleared | VERIFIED | viewer.html:102-106 calls `clearHighlight()`, sets `scrollTop = 0` for both panels inside `loadFile()` |

**Score:** 11/11 truths verified (5 require browser confirmation for interactive/visual behavior)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app.py` | GET /files and GET / routes | VERIFIED | Lines 483-497; both routes present, substantive, fully wired to pathlib glob and render_template |
| `templates/viewer.html` | Complete single-page viewer >= 200 lines | VERIFIED | 211 lines; complete implementation with inline CSS and JS, no stubs |
| `tests/test_app.py` | TestFilesEndpoint and TestViewerRoute test classes | VERIFIED | Lines 520-584; both classes present with 4+2 test methods; all 6 pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py:list_files` | `output_dir/alto/*.xml` | pathlib glob | VERIFIED | `alto_dir.glob('*.xml')` at app.py:490 |
| `app.py:viewer` | `templates/viewer.html` | render_template | VERIFIED | `render_template('viewer.html')` at app.py:497 |
| `templates/viewer.html:DOMContentLoaded` | `/files` | fetch('/files') | VERIFIED | viewer.html:70: `const resp = await fetch('/files')` |
| `templates/viewer.html:loadFile` | `/alto/<stem>` | fetch(`/alto/${stem}`) | VERIFIED | viewer.html:112: `fetch('/alto/${stem}').then(r => r.json())` |
| `templates/viewer.html:tiff-img.src` | `/image/<stem>` | img.src = `/image/${stem}` | VERIFIED | viewer.html:109: `img.src = '/image/${stem}'` |
| `templates/viewer.html:ResizeObserver` | `showHighlight(activeWord)` | ResizeObserver callback | VERIFIED | viewer.html:178-181: observer callback checks `activeWord !== null` then calls `showHighlight` |
| `templates/viewer.html:showHighlight` | `img.clientWidth / pageWidth` | scale factor computation | VERIFIED | viewer.html:158-159: `const scaleX = img.clientWidth / pageWidth` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| VIEW-01 | 11-01-PLAN.md, 11-02-PLAN.md | User can browse all previously processed files in a file list panel | SATISFIED | GET /files returns sorted stems; sidebar renders from that response; all 4 TestFilesEndpoint tests pass |
| VIEW-04 | 11-02-PLAN.md | User can navigate to the previous/next file with keyboard or buttons | SATISFIED | Prev/Next buttons wired via setupNavButtons(); Left/Right arrow keys wired via setupKeyboard(); disabled state managed in loadFile() |
| OVLY-01 | 11-02-PLAN.md | Clicking a word in the text panel highlights its bounding box on the TIFF image | SATISFIED (browser confirmation pending) | selectWord() -> showHighlight() draws SVG rect using ALTO hpos/vpos/width/height scaled by img.clientWidth/pageWidth; pointer-events:all set on rect when visible |
| OVLY-02 | 11-02-PLAN.md | Bounding box coordinates scale correctly as the image is resized | SATISFIED (browser confirmation pending) | ResizeObserver on img element calls showHighlight(activeWord) on any resize; scale uses clientWidth (rendered size) not naturalWidth |

**Orphaned requirements check:** VIEW-02 and VIEW-03 are mapped to Phase 10 in REQUIREMENTS.md — confirmed not claimed by Phase 11 plans and not orphaned here.

### Anti-Patterns Found

None. No TODO/FIXME/PLACEHOLDER/stub patterns detected in `templates/viewer.html` or the Phase 11 additions to `app.py`. The viewer.html is a complete 211-line implementation with all functions substantive.

### Human Verification Required

#### 1. SVG Bounding Box Visual Accuracy

**Test:** Start `python app.py`, open `http://localhost:5000/`, click a file with known ALTO coordinates, then click a word in the text panel.
**Expected:** A semi-transparent yellow rectangle with orange stroke appears visually over the correct word region in the TIFF image thumbnail.
**Why human:** Scale-factor math (`img.clientWidth / pageWidth`) is correct in code but visual accuracy of the overlay position over real OCR content can only be confirmed in a browser with actual data.

#### 2. ResizeObserver Rect Reposition

**Test:** With a file loaded and a word selected (rect visible), drag the browser window to a different size.
**Expected:** The SVG rect stays correctly aligned with the word — it does not shift, disappear, or remain at its old pixel position.
**Why human:** ResizeObserver is a browser API; pytest cannot simulate it.

#### 3. Bidirectional Click: SVG Rect to Text Panel

**Test:** Click a word span to draw the SVG rect, then click the yellow rect itself.
**Expected:** The text panel scrolls so the corresponding word span is visible and gains `selected` CSS (bold + yellow background).
**Why human:** `scrollIntoView()` and DOM scroll are browser-only behaviors.

#### 4. Left/Right Arrow Key Navigation With INPUT Guard

**Test:** (a) Press Left/Right arrow keys while no input is focused — verify files change. (b) Click or tab into an INPUT element and press arrow keys — verify no navigation occurs.
**Expected:** Navigation works freely, suppressed when INPUT is focused.
**Why human:** Key events and focus state require a live browser.

#### 5. Previous/Next Button Disabled Visual State at Boundaries

**Test:** Navigate to the first file; observe Prev button. Navigate to the last file; observe Next button.
**Expected:** Prev is visually grayed out (opacity 0.4) at first file; Next is visually grayed out at last file. Both begin disabled on page load.
**Why human:** CSS `opacity: 0.4` on `:disabled` requires browser rendering; pytest only checks HTTP status.

### Gaps Summary

No automated gaps found. All 11 truths are implemented with substantive code and proper wiring. All 4 requirement IDs (VIEW-01, VIEW-04, OVLY-01, OVLY-02) are satisfied by the implementation. The full test suite (26 tests) passes with no regressions.

The 5 human verification items above cover interactive behaviors (scroll, resize, keyboard) and visual accuracy (SVG position) that are inherently browser-only. These are not blockers to marking the phase complete if a human operator confirms them in the browser — the SUMMARY.md records that the author ran all 10 browser checks and approved them, including the bidirectional click cross-reference, resize stability, and keyboard navigation.

---

_Verified: 2026-02-28T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
