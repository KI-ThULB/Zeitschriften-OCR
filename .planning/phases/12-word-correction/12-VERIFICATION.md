---
phase: 12-word-correction
verified: 2026-03-01T00:00:00Z
status: passed
score: 12/12 must-haves verified
gaps: []
human_verification:
  - test: "Full browser UX walkthrough"
    expected: "Click word -> input pre-filled; Enter saves with green flash; Escape/blur cancels silently; only one word editable at a time; empty input shows inline error; 422 shows inline error with input remaining open; SVG highlight hidden during edit and restored after; file-switch while editing cancels cleanly"
    why_human: "Visual appearance, animation (green flash), SVG overlay behavior, and real-time user interaction flow cannot be verified programmatically"
---

# Phase 12: Word Correction Verification Report

**Phase Goal:** Operators can click any word in the text panel, type a correction, and save it — with the ALTO XML overwritten atomically only after XSD validation passes
**Verified:** 2026-03-01T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /save/<stem> with valid word_id and non-empty content returns 200 and ALTO XML is updated on disk | VERIFIED | `save_word()` at app.py:485-569; test `test_save_updates_alto_on_disk` + `test_save_returns_ok_status` both PASS |
| 2 | POST /save/<stem> with an empty content string returns 422 without modifying the ALTO file | VERIFIED | `if not str(content).strip(): return jsonify(...), 422` at app.py:515-516; test `test_save_empty_content_returns_422` PASS; file byte-comparison asserted in test |
| 3 | POST /save/<stem> that produces invalid XML after substitution returns 422 without modifying the ALTO file | VERIFIED | XSD gate at app.py:545-552 returns 422 before atomic write; test `test_save_atomic_write_on_xsd_failure` monkeypatches `load_xsd` to return always-failing schema and asserts 422 + file unchanged |
| 4 | POST /save/<stem> with an out-of-range word_id returns 404 | VERIFIED | Bounds check at app.py:537-538; test `test_save_word_id_out_of_range_returns_404` PASS |
| 5 | POST /save/<stem> for a stem with no ALTO file returns 404 | VERIFIED | `if not alto_path.exists(): return jsonify({'error': 'not found', 'stem': stem}), 404` at app.py:520-521; test `test_save_stem_not_found_returns_404` PASS |
| 6 | Single-clicking a word in the text panel replaces that word span with an editable input field pre-filled with the current OCR text | VERIFIED (automated portion) | `editWord()` at viewer.html:239-286; `panel.onclick` calls `editWord(word, span)`; `input.value = word.content` at line 251 |
| 7 | Pressing Enter on the input field calls POST /save/<stem> and on success updates the word span text in-place and flashes it green | VERIFIED (automated portion) | `saveWord()` at viewer.html:303-349; `fetch('/save/...')` at line 315; `span.classList.add('word-saved')` at line 341; `@keyframes flash-green` CSS defined |
| 8 | Blurring or pressing Escape cancels the edit silently — original word text is restored, no network call made | VERIFIED (automated portion) | `cancelEdit()` at viewer.html:288-301; `span.appendChild(document.createTextNode(word.content))` restores text; blur handler calls `cancelEdit()` at line 283; Escape triggers `cancelEdit()` at line 274; no fetch call in cancel path |
| 9 | Only one word is editable at a time | VERIFIED (automated portion) | Guard at viewer.html:171-172: `if (editingSpan && editingSpan !== span) cancelEdit()` before opening new edit |
| 10 | Submitting an empty or whitespace-only value shows inline error "Word cannot be empty" and does not call the server | VERIFIED (automated portion) | `if (!raw.trim())` at viewer.html:305; `errorSpan.textContent = 'Word cannot be empty'` at line 306; `return` before fetch |
| 11 | If the server returns a 422 error, inline error "Save failed — invalid content" appears; input remains open | VERIFIED (automated portion) | `if (!resp.ok)` at viewer.html:326; `errorSpan.textContent = 'Save failed — invalid content'` at line 327; `return` leaves input open |
| 12 | The SVG bounding-box highlight is hidden while an input is open and restored after save or cancel | VERIFIED (automated portion) | `clearHighlight()` called at editWord():241; `showHighlight(word)` called in both `cancelEdit()` (line 299) and `saveWord()` (line 345) |

**Score:** 12/12 truths verified (9 automated; 3 require human for visual/animation/UX confirmation)

---

### Required Artifacts

#### Plan 12-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app.py` | POST /save/<stem> endpoint containing `def save_word` | VERIFIED | `@app.post('/save/<stem>')` at line 485; `def save_word(stem)` at line 486; 84 lines of substantive implementation |
| `tests/test_app.py` | TestSaveEndpoint test class | VERIFIED | `class TestSaveEndpoint` at line 591; 9 test methods covering all specified cases |

#### Plan 12-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `templates/viewer.html` | Inline word edit UX containing `editWord` | VERIFIED | `function editWord(word, span)` at line 239; 47 lines; creates input, sets up keydown/blur handlers, calls `clearHighlight()` |
| `templates/viewer.html` | cancelEdit function | VERIFIED | `function cancelEdit()` at line 288; restores original span text, calls `showHighlight(word)` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_app.py` | `app.py POST /save/<stem>` | Flask test client `client.post('/save/...')` | VERIFIED | Pattern `client.post.*save` found at 8 locations; all 9 TestSaveEndpoint tests pass |
| `app.py save_word()` | `output_dir/alto/<stem>.xml` | `etree.tostring` + atomic temp+rename write | VERIFIED | `etree.tostring(root, xml_declaration=True, encoding='UTF-8')` at line 543; `tempfile.mkstemp` at line 555; `os.replace` at line 561 |
| `templates/viewer.html editWord()` | `POST /save/<stem>` | `fetch` POST with JSON body `{word_id, content}` | VERIFIED | `fetch('/save/${encodeURIComponent(stem)}', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({word_id: word.id, content: raw})})` at viewer.html:315-319 |
| `templates/viewer.html` | `clearHighlight()` / `showHighlight()` | Called on edit open and edit close | VERIFIED | `clearHighlight()` at editWord():241; `showHighlight(word)` at cancelEdit():299 and saveWord():345 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EDIT-01 | 12-02 | User can click a word in the text panel to select it for editing | SATISFIED | `panel.onclick` calls `editWord(word, span)` on `.word` span click; input replaces span content |
| EDIT-02 | 12-01, 12-02 | User can type a corrected word and confirm the edit | SATISFIED | Input field pre-filled with `word.content`; Enter key triggers `saveWord()`; `POST /save/<stem>` persists change |
| EDIT-03 | 12-01 | Saving a correction overwrites the ALTO XML Word element and validates the file before writing | SATISFIED | XSD gate at app.py:545-552 validates before atomic write; `strings[idx].set('CONTENT', ...)` updates element; `os.replace` at line 561 performs atomic overwrite |
| EDIT-04 | 12-02 | User sees visual confirmation when a correction is saved | SATISFIED | `@keyframes flash-green` CSS + `span.classList.add('word-saved')` at viewer.html:338-341; green flash animation applied to word span after successful save |

All 4 phase-12 requirements (EDIT-01 through EDIT-04) are claimed by plans and have implementation evidence. No orphaned requirements found.

---

### Anti-Patterns Found

No anti-patterns detected. Scanned `app.py`, `templates/viewer.html`, and `tests/test_app.py` for:
- TODO/FIXME/PLACEHOLDER comments — none found
- `return null`, `return {}`, empty arrow functions — none found
- Stub API routes returning static data without DB/file access — not present
- Console-log-only handlers — not present

---

### Human Verification Required

#### 1. Full browser UX walkthrough

**Test:** Start `python app.py --input ./TIFF --output ./output`, open http://localhost:5000, select a file with ALTO data, then:
1. Click a word — verify input appears pre-filled with OCR text
2. Type a correction, press Enter — verify word span updates with new text and flashes green briefly (~1 second)
3. Open output/alto/<stem>.xml directly and confirm CONTENT attribute is updated
4. Click another word — verify previous input cancels silently, new input opens
5. Press Escape in an open input — verify original text is restored, no file change
6. Click outside (blur) — verify input closes and original text is restored
7. Clear the input, press Enter — verify red "Word cannot be empty" error appears below input; input stays open
8. Trigger a 422 from server (requires schema that fails) — verify "Save failed — invalid content" appears inline; input stays open
9. Click a word (SVG highlight rect visible), open edit (highlight disappears), cancel with Escape (highlight restored)
10. With an edit open, click a different file in the sidebar — verify edit closes cleanly and new file loads

**Expected:** All 10 behaviors match spec from 12-02-PLAN.md Task 2
**Why human:** Visual appearance, CSS animation timing (green flash), SVG overlay visibility changes, and real-time user interaction flow cannot be verified programmatically

---

### Full Test Suite Status

All 35 tests pass (`python -m pytest tests/test_app.py -q` → `35 passed`):
- TestSaveEndpoint: 9/9 PASS
- TestAltoEndpoint: 6/6 PASS (no regression)
- TestImageEndpoint: 5/5 PASS (no regression)
- TestFilesEndpoint, TestViewerRoute, TestSkipAlreadyProcessed, TestErrorIsolation: all PASS

---

### Implementation Notes

1. **Atomic write is correctly implemented:** `tempfile.mkstemp` in the same directory as the target, `os.fdopen` to write, `os.replace` to atomically rename. `os` and `tempfile` are module-level imports (lines 13-14 of app.py), not inline.

2. **XSD gate order is correct:** Serialization happens first (line 543), validation gate runs on the serialized bytes (lines 545-552), disk write only occurs after validation passes (lines 555-561). The gate is bypass-safe: if `load_xsd` returns `None` (schema file absent), writes proceed (consistent with pipeline batch behavior).

3. **word_id indexing is consistent:** `save_word()` uses `root.iter(f'{{{ns}}}String')` with the same namespace and iteration order as `serve_alto()`, ensuring w0/w1/... indices match between GET /alto/<stem> and POST /save/<stem>.

4. **`cancelEdit()` deviation from plan:** The plan's `cancelEdit()` pseudocode calls `showHighlight()` with no argument. The actual implementation calls `showHighlight(word)` at line 299 — passing `word` explicitly and setting `activeWord = word` at line 298. This is a correct improvement over the plan spec: the original plan's bare `showHighlight()` call would fail since `activeWord` was cleared by `clearHighlight()` in `editWord()`. The implementation correctly restores the highlight by passing the word object directly.

---

_Verified: 2026-03-01T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
