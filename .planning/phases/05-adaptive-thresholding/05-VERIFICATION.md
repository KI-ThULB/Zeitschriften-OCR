---
phase: 05-adaptive-thresholding
verified: 2026-02-25T00:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 5: Adaptive Thresholding Verification Report

**Phase Goal:** Scans with uneven illumination can be binarized using adaptive Gaussian thresholding when the operator opts in, without affecting the default pipeline behavior
**Verified:** 2026-02-25
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                      | Status     | Evidence                                                                                                                          |
| --- | -------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Running `pipeline.py` without `--adaptive-threshold` never calls `adaptive_threshold_image()` (default path unchanged)    | ✓ VERIFIED | Guard `if adaptive_threshold:` at line 363 — function only called when bool is True; `False` is hardcoded in `executor.submit()` |
| 2   | Running `pipeline.py --adaptive-threshold` applies Gaussian block-based binarization after deskew and before crop         | ✓ VERIFIED | Call order confirmed: deskew_image (char 13211) → if adaptive_threshold: (char 13839) → detect_crop_box (char 14063)             |
| 3   | `python pipeline.py --help` lists `--adaptive-threshold` with a description mentioning uneven illumination                | ✓ VERIFIED | `--adaptive-threshold  Apply adaptive Gaussian thresholding before OCR (improves results on scans with uneven illumination; off by default)` |
| 4   | `adaptive_threshold_image()` is a pure function: accepts PIL Image, returns binary PIL Image (mode 'L', values 0/255)     | ✓ VERIFIED | Functional tests pass: mode='L', values subset of {0, 255}, size preserved, no disk writes, no side effects                     |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact      | Expected                                                    | Status     | Details                                                                                      |
| ------------- | ----------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------- |
| `pipeline.py` | `adaptive_threshold_image()` pure function                  | ✓ VERIFIED | Lines 128-159; uses `cv2.ADAPTIVE_THRESH_GAUSSIAN_C` + `cv2.THRESH_BINARY`; in-memory only  |
| `pipeline.py` | `ADAPTIVE_BLOCK_SIZE = 51` and `ADAPTIVE_C = 10` constants  | ✓ VERIFIED | Lines 41-44; after `DESKEW_MAX_ANGLE`; both carry empirical tuning notes                    |
| `pipeline.py` | `--adaptive-threshold` argparse flag wired end-to-end       | ✓ VERIFIED | Lines 768-773 (argparse); line 837 (`args.adaptive_threshold` passed to `run_batch()`); line 698 (`executor.submit()` includes `adaptive_threshold`) |

---

### Key Link Verification

| From                          | To                                | Via                                                      | Status     | Details                                                                                     |
| ----------------------------- | --------------------------------- | -------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------- |
| `pipeline.py:process_tiff()`  | `pipeline.py:adaptive_threshold_image()` | `if adaptive_threshold:` guard after deskew, before crop | ✓ WIRED    | Line 363: `if adaptive_threshold:` / line 364: `img = adaptive_threshold_image(img)` |
| `pipeline.py:run_batch()`     | `pipeline.py:process_tiff()`      | `executor.submit()` passes `adaptive_threshold` positional arg | ✓ WIRED    | Line 698: `executor.submit(process_tiff, tiff_path, output_dir, lang, psm, padding, False, adaptive_threshold)` |
| `pipeline.py:main()`          | `pipeline.py:run_batch()`         | `args.adaptive_threshold` passed to `run_batch()`        | ✓ WIRED    | Lines 835-838: `run_batch(..., args.adaptive_threshold,)` |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                                     | Status      | Evidence                                                                                                                     |
| ----------- | ----------- | --------------------------------------------------------------------------------------------------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------- |
| PREP-04     | 05-01-PLAN  | Pipeline applies adaptive thresholding (Gaussian block-based) to improve binarization on scans with uneven illumination before OCR | ✓ SATISFIED | `cv2.adaptiveThreshold(..., cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block_size, c)` called inside `process_tiff()` after deskew and before crop (lines 150-157, 363-364) |
| PREP-05     | 05-01-PLAN  | Adaptive thresholding is opt-in via `--adaptive-threshold` flag (off by default); deskew is always applied     | ✓ SATISFIED | `--adaptive-threshold` argparse flag with `action='store_true'` (default `False`); `if adaptive_threshold:` guard ensures deskew always runs and adaptive threshold only runs when flag set |

No orphaned requirements: REQUIREMENTS.md maps only PREP-04 and PREP-05 to Phase 5, and both are claimed and verified by 05-01-PLAN.

---

### Anti-Patterns Found

| File          | Line  | Pattern           | Severity | Impact |
| ------------- | ----- | ----------------- | -------- | ------ |
| `pipeline.py` | none  | —                 | —        | None   |

No TODO/FIXME patterns found. `adaptive_threshold_image()` is not a stub. No disk writes in the new function. `adaptive_threshold_image()` appears exactly twice: once in the function definition and once inside the `if adaptive_threshold:` guard — no unconditional call path exists.

---

### Human Verification Required

#### 1. OCR quality improvement on uneven illumination scans

**Test:** Run `python pipeline.py --input <dir-with-uneven-illumination-tiffs> --output out_default` and `python pipeline.py --input <same-dir> --output out_adaptive --adaptive-threshold`. Compare word counts and text accuracy in resulting ALTO XML files.
**Expected:** The `--adaptive-threshold` run produces higher word counts and more accurate OCR text on scans with scanner-lid gradient or degraded paper.
**Why human:** OCR quality improvement is a qualitative comparison requiring real corpus scans; cannot be verified programmatically without ground truth.

#### 2. Empirical tuning of ADAPTIVE_BLOCK_SIZE and ADAPTIVE_C

**Test:** Run the pipeline with the real Zeitschriften corpus using `--adaptive-threshold`. Inspect output ALTO XML for OCR quality at the default block_size=51, c=10. Adjust constants if needed.
**Expected:** ADAPTIVE_BLOCK_SIZE=51 and ADAPTIVE_C=10 produce better binarization than global Otsu for the specific corpus; if not, values need empirical tuning.
**Why human:** The PLAN explicitly marks both constants as "NEEDS empirical tuning against real Zeitschriften corpus scans". No ground-truth dataset available for automated comparison.

---

### Gaps Summary

No gaps. All automated checks pass.

- `adaptive_threshold_image()` is substantive: uses `cv2.adaptiveThreshold` with `ADAPTIVE_THRESH_GAUSSIAN_C`, produces binary PIL Image (mode L, values 0/255 only), preserves input dimensions, no side effects.
- Constants `ADAPTIVE_BLOCK_SIZE = 51` (odd, required by cv2) and `ADAPTIVE_C = 10` are defined.
- All three key links (process_tiff → function, run_batch → process_tiff, main → run_batch) are wired and verified.
- Default path is unchanged: `if adaptive_threshold:` guard with bool=False means the function is never called without the flag.
- PREP-04 and PREP-05 are both satisfied. No orphaned requirements.
- Commits fb904d5 (Task 1) and 3d5bbe8 (Task 2) exist in git history.
- `python -m py_compile pipeline.py` exits 0.

The two human verification items are quality-of-life checks on OCR output improvement, not blockers. The implementation is structurally complete and correctly wired.

---

_Verified: 2026-02-25_
_Verifier: Claude (gsd-verifier)_
