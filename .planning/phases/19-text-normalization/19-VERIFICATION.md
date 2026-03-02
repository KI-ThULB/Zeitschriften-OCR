---
phase: 19-text-normalization
verified: 2026-03-02T17:10:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "View a two-column scan in the text panel and confirm left-column words precede right-column words"
    expected: "All words from the left column appear before any word from the right column in the text panel"
    why_human: "Column layout correctness requires a real multi-column ALTO file and visual inspection — cannot be verified programmatically without fixture data"
  - test: "Load a file with a hyphenated line break (e.g. 'Ver-' at line end + 'bindung' on next line) and inspect the text panel"
    expected: "The word appears as 'Verbindung' — no trailing hyphen visible, no space between fragments"
    why_human: "Requires real ALTO XML with a genuine hyphenated compound split across TextLines"
  - test: "Drag the confidence threshold slider to 0.9 — observe faded words; drag to 0.1 — observe recovery"
    expected: "Words below threshold fade to ~40% opacity in real time; badge count updates; tooltip shows 'Confidence: 0.XX' on hover"
    why_human: "Real-time opacity behavior, tooltip display, and badge accuracy require a live browser session with WC-tagged ALTO data"
  - test: "Reload the page after adjusting the confidence threshold slider"
    expected: "Slider restores to the previously set value from localStorage"
    why_human: "localStorage persistence requires a running browser session"
  - test: "Click a word that was rejoined from a hyphenated pair and confirm the edit input shows the un-rejoined ALTO content"
    expected: "Edit dialog shows 'Ver-' (original first fragment), not 'Verbindung'; save writes the original word_id back to ALTO XML"
    why_human: "Click-to-edit behavior on rejoined words requires a running browser session"
---

# Phase 19: Text Normalization Verification Report

**Phase Goal:** Users see a clean, correctly ordered word stream — columns read left-to-right, hyphens rejoined, low-confidence words visually flagged
**Verified:** 2026-03-02T17:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User views a two-column scan and words appear in left-column-first order | ? NEEDS HUMAN | columnSort() exists and is fully wired; logic verified; no test fixture for two-column rendering |
| 2 | A word split with a hyphen (e.g. "Ver-" + "bindung") appears rejoined as "Verbindung" in text panel | ? NEEDS HUMAN | rejoinHyphens() wired in normalizeWords(); logic verified; real ALTO fixture needed |
| 3 | User can set confidence threshold; words below appear faded | ? NEEDS HUMAN | applyConfidenceStyling() wired; slider HTML present; localStorage init present; browser needed |
| 4 | Original ALTO XML is unchanged — normalization is display-only | VERIFIED | wordById always maps data.words (not displayWords); no write call from normalization path; applyConfidenceStyling mutates only DOM opacity |

**Automated score:** 4/4 truths have complete implementation (code verified). 3 truths need human confirmation for runtime behavior.

### Required Artifacts

#### Plan 19-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app.py` | serve_alto() returns blocks array and line_end per word | VERIFIED | `blocks_out` built at line 560; `last_in_line` set at line 518; `'blocks': blocks_out` in jsonify return at line 583; `'line_end': i in last_in_line` at line 549 |
| `tests/test_app.py` | Tests for blocks array shape and line_end flag correctness | VERIFIED | `test_alto_blocks_array` (line 434), `test_alto_line_end_flag` (line 514), `test_alto_blocks_empty_when_no_textblocks` (line 572) — all pass |

#### Plan 19-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `templates/viewer.html` | `function normalizeWords`, `columnSort`, `clusterByHpos`, `rejoinHyphens` | VERIFIED | All four functions present at lines 361–462; fully implemented, not stubs |
| `templates/viewer.html` | `applyConfidenceStyling()`, confidence slider, WC badge | VERIFIED | `applyConfidenceStyling` at line 472; `#wc-settings` slider at line 166–174; `#wc-badge` at line 173 |
| `templates/viewer.html` | `data-wc` attribute on word spans | VERIFIED | `renderWords()` emits `data-wc="${w.confidence ?? ''}"` at line 505 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app.py serve_alto()` | `blocks_out` array in response | `elem_to_idx` positional index map | WIRED | `elem_to_idx` built at line 515; `blocks_out` assembled at lines 560–576; returned in jsonify at line 583 |
| `app.py serve_alto()` | `line_end` per word | `last_in_line` set from TextLine.iter(String) | WIRED | `last_in_line` computed at lines 519–535 with lxml-proxy-safe fallback; used at line 549 |
| `loadFile()` in viewer.html | `normalizeWords(data.words, data.blocks, data.page_width)` | Replaces direct `renderWords(data.words)` call | WIRED | Line 342: `displayWords = normalizeWords(data.words, data.blocks \|\| [], data.page_width)` — direct renderWords(data.words) no longer present |
| `applyConfidenceStyling()` | `.word[data-wc]` spans | `querySelectorAll` + `style.opacity` | WIRED | Line 474: `document.querySelectorAll('.word[data-wc]').forEach(span => {...})` — opacity set without DOM rebuild |
| `wc-slider input event` | `localStorage.setItem + applyConfidenceStyling` | real-time update on `input` event | WIRED | Lines 235–240: `addEventListener('input', ...)` sets wcThreshold, writes localStorage, calls `applyConfidenceStyling(wcThreshold)` |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| TEXT-01 | 19-01, 19-02 | Words delivered in correct multi-column reading order (left-to-right, then top-to-bottom within each column) | SATISFIED | `columnSort()` + `clusterByHpos()` implement full-width-first, then left-right column clustering; wired into `loadFile()` via `normalizeWords()` |
| TEXT-02 | 19-01, 19-02 | Rejoins German end-of-line hyphenated words for display; original split preserved in ALTO | SATISFIED | `rejoinHyphens()` uses `line_end` flag from API; joined word inherits first fragment's id; `wordById` maps original `data.words` — ALTO unmodified |
| TEXT-03 | 19-02 | User can configure minimum word-confidence threshold; words below it are visually marked | SATISFIED | `applyConfidenceStyling()` fades words to opacity 0.4; threshold slider range 0–1 step 0.05; `wcThreshold` persisted via `localStorage`; `wc-badge` shows count |

No orphaned requirements: REQUIREMENTS.md marks TEXT-01, TEXT-02, TEXT-03 as Complete / Phase 19. All three are claimed and implemented across 19-01 and 19-02.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None found |

Scanned `app.py` (serve_alto region) and `templates/viewer.html` for TODO/FIXME, placeholder returns (return null, return {}, return []), console.log-only handlers, stub onSubmit, empty implementations. No anti-patterns detected.

### Human Verification Required

#### 1. Two-column reading order

**Test:** Open a two-column archival scan in the viewer text panel (requires a real multi-column TIFF with corresponding ALTO XML containing multiple TextBlock elements with distinct HPOS values)
**Expected:** All words from the left column appear before any word from the right column in the text panel — words are not interleaved top-to-bottom across columns
**Why human:** The columnSort() algorithm is code-verified but its correctness for real newspaper layouts requires a genuine multi-column ALTO fixture; no such fixture exists in the automated test suite

#### 2. Hyphen rejoin display

**Test:** Load a file where the ALTO XML contains a TextLine ending with a String whose CONTENT ends in "-" and line_end=true, followed by the first word of the next line
**Expected:** The text panel shows the rejoined word (e.g. "Verbindung") with no trailing hyphen and no space between fragments
**Why human:** No automated test fixture exists with a genuine hyphenated compound split across TextLines; end-to-end display requires a running browser

#### 3. Confidence threshold fading and badge

**Test:** Load a file with words that have WC attributes; drag the slider to 0.9
**Expected:** Words below WC 0.9 fade to approximately 40% opacity; the wc-badge below the slider shows the count (e.g. "42 low-confidence words"); hovering a faded word shows a tooltip "Confidence: 0.XX"
**Why human:** Real-time CSS opacity mutation, tooltip display, and badge text require a live browser with WC-tagged ALTO data

#### 4. localStorage persistence

**Test:** Set the threshold slider to 0.7, close the tab, reopen the viewer
**Expected:** Slider initializes to 0.70 and label reads "0.70"
**Why human:** localStorage behavior requires a running browser session; cannot be tested via pytest

#### 5. Click-to-edit on rejoined words

**Test:** With a hyphenated word rejoined in the display, click on it to open the inline edit input
**Expected:** The input field shows the original first fragment (e.g. "Ver-"), not the rejoined form; saving writes the word_id of the first fragment back to the ALTO XML
**Why human:** Requires a browser session with a real rejoined word visible in the text panel

### Gaps Summary

No gaps. All automated checks pass. Both plans delivered complete, wired implementations:

- Plan 19-01: `serve_alto()` in `app.py` extended with `blocks` array (TextBlock geometry + word_ids) and `line_end` boolean per word. lxml proxy recycling handled correctly via materialized `all_strings` list. Three new TestAltoEndpoint tests added; 136 total tests pass.

- Plan 19-02: `templates/viewer.html` extended with `clusterByHpos()`, `columnSort()`, `rejoinHyphens()`, `normalizeWords()`, `applyConfidenceStyling()`, confidence threshold slider (#wc-settings), WC badge, and `data-wc` attribute on word spans. `normalizeWords()` is wired into `loadFile()` replacing the direct `renderWords(data.words)` call. `wordById` correctly maps original `data.words` (not displayWords), preserving edit/save behavior on ALTO-original content. The `#word-list` inner container pattern ensures the persistent slider HTML survives `renderWords()` innerHTML replacements.

---

_Verified: 2026-03-02T17:10:00Z_
_Verifier: Claude (gsd-verifier)_
