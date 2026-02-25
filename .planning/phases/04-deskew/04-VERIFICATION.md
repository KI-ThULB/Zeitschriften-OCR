---
phase: 04-deskew
verified: 2026-02-25T17:50:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Run a batch on real archival TIFFs with known skew"
    expected: "Result line shows [deskew: N.N°] with non-zero angle; output ALTO files contain correctly aligned bounding boxes"
    why_human: "Unit tests mock determine_skew; only real scans with actual skew confirm the Hough detection produces valid angles in practice"
---

# Phase 4: Deskew Verification Report

**Phase Goal:** Every TIFF is automatically rotated to upright orientation before OCR, with the correction angle visible in run output and graceful handling of detection failures
**Verified:** 2026-02-25T17:50:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                                                      | Status     | Evidence                                                                                                                                                             |
|----|--------------------------------------------------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | Every TIFF passes through deskew_image() automatically before crop and OCR — no manual pre-rotation needed                                 | VERIFIED   | `process_tiff()` calls `deskew_image(img)` at line 308, before `detect_crop_box(img)` at line 325; positions 11521 vs 12226 confirmed programmatically               |
| 2  | Each per-file result line includes a `[deskew: N.N°]` annotation showing the detected angle                                               | VERIFIED   | `deskew_str = f'[deskew: {deskew_angle:.1f}\u00b0]'` (line 319) is appended to result line via `deskew_suffix` (line 351–352); confirmed in output line format       |
| 3  | When deskew detection returns None or an implausible angle (>10°), process_tiff() uses the original image and appends a WARN string; the batch does not abort | VERIFIED   | Lines 310–315: `None` → `'deskew: detection failed, using original orientation'`; implausible → `f'deskew: implausible angle {deskew_angle:.1f}°, using original orientation'` appended to `warnings_list`; no sys.exit() called |
| 4  | A scan with near-zero angle (< 0.05°) is returned unchanged without any rotation resampling                                               | VERIFIED   | Line 107–108: `if abs(angle) < 0.05: return image, angle, False` — original image object returned, no `image.rotate()` called; unit test (mock 0.02°) confirms `fallback=False` |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact          | Expected                                         | Status      | Details                                                                                                     |
|-------------------|--------------------------------------------------|-------------|-------------------------------------------------------------------------------------------------------------|
| `requirements.txt` | `deskew>=1.5.0` declared                        | VERIFIED    | Line 3: `deskew>=1.5.0` present; 6 lines total; file substantive with all project deps                     |
| `pipeline.py`      | `deskew_image()` function and `process_tiff()` integration; exports `deskew_image`, `DESKEW_MAX_ANGLE`; min 780 lines | VERIFIED | 820 lines (exceeds 780 minimum); `deskew_image` importable; `DESKEW_MAX_ANGLE = 10.0` at line 39; function at lines 72–120 |

**Level 1 (Exists):** Both files present.
**Level 2 (Substantive):** `requirements.txt` has all 6 dependencies including `deskew>=1.5.0`. `pipeline.py` is 820 lines with full implementations — no placeholder returns, no TODO/FIXME markers found.
**Level 3 (Wired):** `deskew_image()` called in `process_tiff()` at line 308; result unpacked into `img, deskew_angle, deskew_fallback`; `deskew_str` used in result line at line 352.

---

### Key Link Verification

| From                         | To                              | Via                                                       | Status    | Details                                                                                                    |
|------------------------------|---------------------------------|-----------------------------------------------------------|-----------|------------------------------------------------------------------------------------------------------------|
| `pipeline.py:process_tiff()` | `pipeline.py:deskew_image()`   | call after `load_tiff()`, before `detect_crop_box()`      | WIRED     | `deskew_image(img)` at char position 11521; `detect_crop_box(img` at 12226; order verified programmatically |
| `pipeline.py:deskew_image()` | `deskew.determine_skew`         | top-level import + grayscale numpy array                  | WIRED     | `from deskew import determine_skew` at line 25; `gray = np.array(image.convert('L'))` then `determine_skew(gray)` at lines 90–93 |
| `pipeline.py:process_tiff()` | result line stdout              | `deskew_str` built separately from `warnings_list`        | WIRED     | `deskew_str` initialized at line 299; set at lines 316/319; `deskew_suffix` built at line 351; injected into `print()` at line 352 |

All three key links verified.

---

### Requirements Coverage

| Requirement | Source Plan  | Description                                                                                                | Status    | Evidence                                                                                             |
|-------------|--------------|------------------------------------------------------------------------------------------------------------|-----------|------------------------------------------------------------------------------------------------------|
| PREP-01     | 04-01-PLAN.md | Pipeline detects the rotation angle of each scan and corrects it before OCR; applied to every TIFF automatically | SATISFIED | `process_tiff()` unconditionally calls `deskew_image(img)` before crop — no condition gates it off   |
| PREP-02     | 04-01-PLAN.md | Detected rotation angle logged per file in the result line (e.g. `[deskew: 1.4°]`)                        | SATISFIED | `deskew_str = f'[deskew: {deskew_angle:.1f}°]'` wired into result line print at line 352             |
| PREP-03     | 04-01-PLAN.md | If deskew fails or produces an implausible result, pipeline falls back to original orientation and logs a warning; batch continues | SATISFIED | Fallback path appends to `warnings_list` (WARN prefix in output); `deskew_str` set to `''`; no abort |

**Orphaned requirements check:** REQUIREMENTS.md maps PREP-01, PREP-02, PREP-03 to Phase 4. All three appear in 04-01-PLAN.md `requirements` field. No orphaned requirements.

---

### Anti-Patterns Found

| File         | Line | Pattern                             | Severity | Impact                            |
|--------------|------|-------------------------------------|----------|-----------------------------------|
| pipeline.py  | —    | No TODO/FIXME/PLACEHOLDER found     | —        | None                              |
| pipeline.py  | —    | No stub returns (null, {}, [])      | —        | None                              |
| pipeline.py  | —    | No console.log-only handlers        | —        | None                              |

No anti-patterns detected in either modified file.

---

### Commit Verification

Both task commits documented in SUMMARY.md exist and are valid:

| Hash      | Message                                                          | Files Changed                        |
|-----------|------------------------------------------------------------------|--------------------------------------|
| `7536e86` | feat(04-deskew-01): add deskew dependency and implement deskew_image() | `pipeline.py` (+54 lines), `requirements.txt` (+1 line) |
| `e8db9d9` | feat(04-deskew-01): wire deskew_image() into process_tiff() with angle reporting | `pipeline.py` (+17 lines)            |

---

### Human Verification Required

#### 1. Real-scan angle detection accuracy

**Test:** Run `python pipeline.py --input ./path/to/archival_tiffs --output ./output_deskew_test` against actual archival TIFFs that have slight scan-time rotation.
**Expected:** Result lines show non-zero `[deskew: N.N°]` values matching visually observable skew; output ALTO bounding boxes are better aligned than without deskew.
**Why human:** Unit tests mock `determine_skew()`. Only real scans confirm the Hough algorithm produces accurate angles on this corpus's TIFF characteristics (resolution, content type, scanner bed colour).

---

### Automated Verification Suite Results

All four checks from the PLAN verification section passed:

```
python -m py_compile pipeline.py   → Syntax OK
deskew_image() unit checks (6 tests) → All passed
grep 'deskew' requirements.txt     → deskew>=1.5.0 present
Structural order check             → deskew before crop (positions 11521 vs 12226)
```

---

## Summary

Phase 4 goal is fully achieved. The codebase delivers all four observable truths:

1. **Automatic deskew on every TIFF** — `deskew_image()` is an unconditional step in `process_tiff()`, called immediately after `load_tiff()` and before `detect_crop_box()`. No manual pre-rotation is required.

2. **Angle annotation in result line** — Successful corrections produce `[deskew: N.N°]` in stdout. The annotation is separate from `warnings_list` so it appears even when there are no other warnings, exactly matching PREP-02.

3. **Graceful failure handling** — Two distinct fallback paths (detection returned `None`; angle > 10°) append specific warning text to `warnings_list` (which produces `[WARN: ...]` in the result line) and continue processing the original image. No `sys.exit()` or re-raise on the deskew path — the batch does not abort.

4. **Near-zero passthrough** — `abs(angle) < 0.05` returns the original `image` object without calling `image.rotate()`, avoiding resampling artifacts on already-straight scans.

The `deskew_str = ''` initialization before the `try:` block (line 299) eliminates any `NameError` risk on exception paths. All three PREP requirements are satisfied with direct code evidence. No stubs, placeholders, or wiring gaps found.

The only item requiring human judgment is confirming real archival TIFFs produce meaningful angles from the Hough detector — this cannot be verified by static analysis.

---

_Verified: 2026-02-25T17:50:00Z_
_Verifier: Claude (gsd-verifier)_
