# Phase 5: Adaptive Thresholding - Research

**Researched:** 2026-02-25
**Domain:** Image binarization — OpenCV adaptive Gaussian thresholding as opt-in preprocessing for OCR on archival TIFF scans
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PREP-04 | Pipeline applies adaptive thresholding (Gaussian block-based) to improve binarization on scans with uneven illumination before OCR | `cv2.adaptiveThreshold()` with `ADAPTIVE_THRESH_GAUSSIAN_C` provides exactly this; input is a grayscale uint8 numpy array, output is a binary uint8 array convertible back to PIL Image for `run_ocr()` |
| PREP-05 | Adaptive thresholding is opt-in via `--adaptive-threshold` flag (off by default); deskew is always applied | `argparse` `action='store_true'` pattern — identical to `--force` and `--validate-only` in the existing CLI; default is `False` unless the flag is present |
</phase_requirements>

---

## Summary

Adaptive thresholding for this project means applying a local Gaussian-weighted binarization step to each scan, in memory, immediately before the image is passed to Tesseract. The problem it solves is uneven illumination: archival periodical scans often have gradient lighting from a flatbed scanner lid or degraded paper — global Otsu thresholding (used elsewhere in the pipeline for crop detection) handles this poorly for text binarization. `cv2.adaptiveThreshold()` with `ADAPTIVE_THRESH_GAUSSIAN_C` computes a per-pixel threshold from a local neighbourhood, adapting to local brightness variations.

The entire feature is already deliverable using `opencv-python-headless` and `Pillow`, both of which are already in `requirements.txt`. No new dependencies are needed. The conversion chain is: PIL Image → grayscale numpy uint8 array → `cv2.adaptiveThreshold()` → binary uint8 array → `Image.fromarray(..., 'L')` back to PIL Image. The returned PIL Image is then passed to `run_ocr()` exactly as the cropped image is today.

The opt-in requirement (PREP-05) follows the exact same `action='store_true'` argparse pattern as the existing `--force` and `--validate-only` flags. Wiring `adaptive_threshold: bool` through `process_tiff()` and `run_batch()` follows the same pattern as the existing `no_crop: bool` parameter.

The key concern from STATE.md — "Adaptive threshold block size and C constant need tuning against real Zeitschriften scans" — is addressed below. Research confirms `block_size=51, C=10` as a starting point for high-resolution archival scans (300+ DPI), with the values exposed as named constants so they can be adjusted without a code audit. The planner MUST flag these values as requiring empirical validation against a sample of real corpus scans before the phase is considered complete.

**Primary recommendation:** No new dependencies. Implement `adaptive_threshold_image()` as a pure function that takes a PIL Image and returns a PIL Image (binary, mode 'L'). Wire it into `process_tiff()` as a conditional step (only when `adaptive_threshold=True`) after deskew and before crop detection. Expose `--adaptive-threshold` in argparse with `action='store_true'`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `opencv-python-headless` | >=4.9.0 (already in requirements.txt) | `cv2.adaptiveThreshold()` — Gaussian adaptive binarization | Already a project dependency; `adaptiveThreshold` is the standard OpenCV function for local threshold binarization; no additional install needed |
| `Pillow` | >=11.1.0 (already in requirements.txt) | PIL Image ↔ numpy array round-trip; `Image.fromarray()` to return PIL Image from binary numpy array | Already a project dependency; `Image.fromarray(array, 'L')` converts the uint8 numpy output of `adaptiveThreshold` back to PIL mode 'L' |
| `numpy` | transitive via opencv + deskew | `np.array(img.convert('L'))` for PIL-to-grayscale-array conversion | Already present transitively; same conversion used in `deskew_image()` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None required | — | — | All needed libraries are already in requirements.txt |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cv2.adaptiveThreshold` with `ADAPTIVE_THRESH_GAUSSIAN_C` | `ADAPTIVE_THRESH_MEAN_C` | Mean method uses a simple unweighted average of the neighbourhood; Gaussian method gives more weight to pixels near the centre of the window, producing smoother results for text with slight blur — Gaussian is preferred for OCR preprocessing |
| `cv2.adaptiveThreshold` | `skimage.filters.threshold_sauvola` | Sauvola is a more sophisticated local method designed specifically for document binarization in poor conditions; adds `scikit-image` dependency (already present transitively via `deskew`). PREP-04 explicitly specifies Gaussian block-based — implement as specified; Sauvola is out of scope |
| `cv2.adaptiveThreshold` | Global Otsu (`cv2.THRESH_OTSU`) | Otsu already used in `detect_crop_box()` for the crop step; it fails on uneven illumination (the exact problem PREP-04 addresses); not an alternative for this requirement |

**Installation:** No new packages needed. All required libraries are already declared in `requirements.txt`.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. All adaptive threshold logic lives in `pipeline.py` as a single new function, following the same pattern as `deskew_image()`:

```
pipeline.py
├── load_tiff()                    → (PIL Image, dpi, warnings)
├── deskew_image()                 → (PIL Image, float | None, bool)     [Phase 4]
├── adaptive_threshold_image()     → PIL Image                           ← NEW in Phase 5
├── detect_crop_box()              → (crop box, fallback_used)
├── run_ocr()                      → ALTO XML bytes
├── build_alto21()                 → ALTO XML bytes
├── count_words()                  → int
└── process_tiff()                 → calls adaptive_threshold_image() conditionally
```

### Pattern 1: adaptive_threshold_image() as a pure function

**What:** A self-contained function that accepts a PIL Image and returns a binarized PIL Image (mode 'L'). The caller decides whether to call it — the function itself does not read any flags.

**When to use:** Called from `process_tiff()` after `deskew_image()` and before `detect_crop_box()` when `adaptive_threshold=True`. On the default path (`adaptive_threshold=False`), this function is not called at all.

**Why this position in the pipeline:** Deskew must run first (axis-aligned page = reliable crop contour). Adaptive threshold must run before crop detection because `detect_crop_box()` does its own Otsu threshold on the image passed to it — if we threshold first, the crop detection benefits from a cleaner binary image. Crop must run before OCR for the existing reason (offset coordinates).

**Correct step order:** load_tiff → deskew_image → adaptive_threshold_image (conditional) → detect_crop_box → crop → run_ocr

**Example:**
```python
# Source: cv2 official docs (https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html)
#         PIL docs (https://pillow.readthedocs.io/en/stable/reference/Image.html)

ADAPTIVE_BLOCK_SIZE = 51   # Must be odd and > 1. Neighbourhood size in pixels.
                           # At 300 DPI, 51px ≈ 4.3mm — spans a few characters of typical
                           # periodical body text. NEEDS empirical tuning vs real corpus.
ADAPTIVE_C = 10            # Constant subtracted from local Gaussian mean.
                           # Positive C raises the threshold (makes fewer pixels white).
                           # NEEDS empirical tuning vs real corpus.

def adaptive_threshold_image(
    image: Image.Image,
    block_size: int = ADAPTIVE_BLOCK_SIZE,
    c: int = ADAPTIVE_C,
) -> Image.Image:
    """Apply adaptive Gaussian thresholding to binarize the image.

    Useful for scans with uneven illumination where global Otsu thresholding
    produces dark or washed-out regions.

    Args:
        image: PIL Image (any mode; converted to grayscale internally)
        block_size: Size of the pixel neighbourhood for computing local threshold.
                    Must be an odd integer >= 3.
        c: Constant subtracted from the weighted local mean.
           Positive values raise the threshold (fewer white pixels).

    Returns:
        Binary PIL Image (mode 'L', values 0 or 255)
    """
    # cv2.adaptiveThreshold requires a uint8 grayscale (single-channel) numpy array
    gray = np.array(image.convert('L'))
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c,
    )
    # binary is already uint8 shape (H, W) — convert directly to PIL
    return Image.fromarray(binary, 'L')
```

### Pattern 2: Integration in process_tiff()

**What:** `adaptive_threshold_image()` is inserted as a conditional step between `deskew_image()` and `detect_crop_box()`. The `process_tiff()` signature gains one new parameter: `adaptive_threshold: bool`.

**Example:**
```python
# process_tiff() signature change
def process_tiff(
    tiff_path: Path,
    output_dir: Path,
    lang: str,
    psm: int,
    padding: int,
    no_crop: bool,
    adaptive_threshold: bool,        # NEW — Phase 5
) -> None:

# Inside process_tiff(), after the deskew block, before detect_crop_box():
        # Adaptive threshold step (PREP-04 / PREP-05: opt-in only)
        if adaptive_threshold:
            img = adaptive_threshold_image(img)
```

### Pattern 3: run_batch() parameter threading

`run_batch()` must accept and pass `adaptive_threshold` through to `executor.submit()`. This follows the identical pattern as `no_crop` (currently hardcoded to `False` in `run_batch()`):

```python
def run_batch(
    tiff_files: list,
    output_dir: Path,
    workers: int,
    lang: str,
    psm: int,
    padding: int,
    force: bool,
    adaptive_threshold: bool,   # NEW — Phase 5
) -> tuple:
    ...
    futures = {
        executor.submit(
            process_tiff, tiff_path, output_dir, lang, psm, padding, False, adaptive_threshold
        ): tiff_path
        for tiff_path in to_process
    }
```

### Pattern 4: argparse flag (PREP-05)

**What:** `--adaptive-threshold` flag using `action='store_true'`. Default is `False` — identical mechanics to `--force` and `--validate-only`.

**Example:**
```python
# Source: https://docs.python.org/3/library/argparse.html
parser.add_argument(
    '--adaptive-threshold',
    action='store_true',
    help='Apply adaptive Gaussian thresholding before OCR (improves results on scans '
         'with uneven illumination; off by default)',
)
```

argparse converts `--adaptive-threshold` to `args.adaptive_threshold` automatically (hyphens → underscores).

### Anti-Patterns to Avoid

- **Calling adaptive_threshold_image() unconditionally:** PREP-05 requires it to be opt-in. A run without `--adaptive-threshold` must produce identical output to a pre-v1.2 run (Success Criterion 1). Any unconditional call violates this.
- **Applying adaptive threshold after crop:** The image passed to `detect_crop_box()` is the full deskewed image. If the adaptive threshold step converts the image to binary before crop, the crop detection may actually work better (cleaner binary edges) — but the crop must still happen before OCR. The correct order is always: deskew → threshold (if enabled) → crop → OCR.
- **Passing a float32 or uint16 array to cv2.adaptiveThreshold():** The function requires `CV_8UC1` (uint8, single channel). `np.array(image.convert('L'))` always produces `uint8` from a PIL image — this is correct. Do not apply any normalization or float conversion before calling `adaptiveThreshold`.
- **Using an even block_size:** `cv2.adaptiveThreshold()` raises an OpenCV error if `block_size` is even or less than 3. Always use an odd integer >= 3.
- **Using THRESH_BINARY_INV:** The project decision (STATE.md) is `THRESH_BINARY` (not INV) for archival scans (dark border, light page). This applies to adaptive thresholding too — do not use `THRESH_BINARY_INV`.
- **Saving the thresholded image to disk:** REQUIREMENTS.md explicitly lists "Saving preprocessed images as deliverables" as out of scope. The binarized image is in-memory only; the original TIFF is never modified.
- **Not adding adaptive_threshold to process_tiff() signature:** The function runs in a `ProcessPoolExecutor` worker via `executor.submit()`. All parameters must be passed as positional arguments — they must be picklable. `bool` is picklable. Do not use a global variable or module-level flag to communicate the setting to workers.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Local threshold computation | Custom per-block mean/Gaussian-weighted threshold loop | `cv2.adaptiveThreshold()` | Handles edge cases (boundary pixels, kernel normalization, blockSize constraints) and runs in C++; a Python loop would be 10-100x slower on 300 DPI TIFFs |
| Grayscale conversion before adaptiveThreshold | Custom RGB→gray formula | `image.convert('L')` + `np.array()` | PIL 'L' mode conversion is ITU-R 601 luma (standard for document images); `np.array()` produces the correct uint8 dtype without any additional casting |
| PIL↔numpy round-trip for thresholding | Custom buffer copy | `np.array()` + `Image.fromarray()` | Both are zero-copy for compatible dtypes and modes; no custom buffer handling needed |
| Boolean flag threading to workers | Global variable, multiprocessing.Value, shared memory | Add `adaptive_threshold: bool` parameter to `process_tiff()` and pass via `executor.submit()` | Matches the existing `no_crop` pattern; bool is picklable; no synchronization needed since it is read-only |

**Key insight:** `cv2.adaptiveThreshold()` is already in the project's dependency tree via `opencv-python-headless`. This phase adds zero new dependencies and zero new files — it is a pure function addition and parameter threading exercise.

---

## Common Pitfalls

### Pitfall 1: Even or too-small block_size causes OpenCV error

**What goes wrong:** `cv2.adaptiveThreshold()` raises `cv2.error: blockSize must be odd and greater than 1` at runtime. The worker raises in `ProcessPoolExecutor`, gets collected as a failed file.
**Why it happens:** The block_size must be an odd integer >= 3. Common mistake is using 50 (even) instead of 51.
**How to avoid:** Name the constant `ADAPTIVE_BLOCK_SIZE` and set it to 51 (odd). Document the odd-and->=3 constraint in the constant's comment and the function docstring. If the planner ever tunes this value, they must verify it is odd.
**Warning signs:** All files fail with `cv2.error` in the JSONL error log mentioning `blockSize`.

### Pitfall 2: Default output changes when --adaptive-threshold is not passed

**What goes wrong:** Success Criterion 1 fails: a run without `--adaptive-threshold` produces different ALTO output than a pre-v1.2 run.
**Why it happens:** The conditional guard in `process_tiff()` is missing or wrong, so `adaptive_threshold_image()` runs unconditionally.
**How to avoid:** Gate the call with `if adaptive_threshold:`. Verify with a structural check that the call is inside the conditional. The `adaptive_threshold` parameter default in `process_tiff()` must be `False` if ever called without it (though in practice `run_batch()` always passes it explicitly).
**Warning signs:** Integration test comparing pre/post output finds differences without `--adaptive-threshold` being passed.

### Pitfall 3: Thresholding destroys the image passed to detect_crop_box()

**What goes wrong:** After `adaptive_threshold_image()` produces a binary image (values 0 or 255), `detect_crop_box()` applies its own Otsu threshold to what is already a binary image. Otsu on a bimodal binary image is still valid (it will compute a threshold near 127), but the all-white/all-black regions in the binarized image may cause `findContours` to return a different largest contour than it would from the original grayscale.
**Why it happens:** The adaptive threshold step converts the image before the crop step sees it.
**How to avoid:** This is a known trade-off, not a bug. Research indicates that binarizing before crop detection generally produces cleaner contours. However, test on real corpus scans — if crop quality degrades (more `crop fallback` warnings), consider running adaptive threshold only after the crop step (i.e., after `img.crop(crop_box)`). The PLAN should note this as a decision point to validate empirically.
**Warning signs:** Increased frequency of `[WARN: crop fallback, using full image]` in run output after enabling `--adaptive-threshold`.

### Pitfall 4: block_size too large blurs away thin strokes in body text

**What goes wrong:** A very large block_size (e.g., 201) makes the local neighbourhood so large that it approaches a global threshold — losing the adaptation benefit. For high-resolution scans (300-600 DPI) with small body text, a block_size of 201px may span 8-15 characters and average out local illumination variation; thin strokes in small type may fall below threshold and be lost.
**Why it happens:** Choosing block_size in pixel units without considering DPI and typical character size.
**How to avoid:** At 300 DPI, 51px ≈ 4.3mm ≈ roughly 2–3 characters of typical periodical body text. This is a reasonable starting neighbourhood. At 600 DPI, consider 101. Document the DPI assumption in the constant comment. The concern in STATE.md ("needs tuning against real Zeitschriften scans") is exactly this — empirical tuning is mandatory.
**Warning signs:** Word count drops significantly compared to the same scan processed without `--adaptive-threshold`; thin-stroke characters (serifs, lowercase 'i', commas) appear broken in ALTO output.

### Pitfall 5: block_size too small amplifies noise

**What goes wrong:** A very small block_size (e.g., 5) treats individual pixel noise as local illumination variation, producing a heavily speckled output where isolated noise pixels become foreground. Tesseract may interpret speckle as characters.
**Why it happens:** Neighbourhood too small to distinguish illumination gradient from noise.
**How to avoid:** For 300 DPI archival scans, a block_size below 11 is typically too small. Start at 51 and tune down only if local contrast is not being captured.
**Warning signs:** Word count significantly higher than expected; ALTO XML contains many short nonsense "words" from noise patches.

### Pitfall 6: C constant sign confusion

**What goes wrong:** Setting `C` to a negative value accidentally lowers the threshold, making more pixels foreground (white), which may be correct for very dark scans but wrong for normal archival scans with light backgrounds.
**Why it happens:** The formula is `threshold = gaussian_mean - C`. A positive C raises the threshold (fewer pixels become white). A negative C lowers it (more pixels become white). The confusion arises because "subtracting a negative" means adding.
**How to avoid:** For archival scans with light backgrounds and dark text, use a positive C (e.g., 10). Only go negative if the scan is underexposed (unusually dark background).
**Warning signs:** Background areas appear as foreground (white) in the binary output; word count explodes.

### Pitfall 7: Forgetting to thread adaptive_threshold through run_batch()

**What goes wrong:** `run_batch()` is called in `main()` but does not accept or pass `adaptive_threshold`, so workers always see `False` regardless of the CLI flag.
**Why it happens:** The parameter is added to `process_tiff()` and `main()` but `run_batch()` is not updated.
**How to avoid:** The PLAN must include updating both `process_tiff()`, `run_batch()`, and the `executor.submit()` call in the same task. Verify with a structural check that `adaptive_threshold` appears in the `submit()` call.
**Warning signs:** `--adaptive-threshold` flag appears to have no effect; no change in output when flag is passed.

---

## Code Examples

Verified patterns from official and cross-verified sources:

### Complete adaptive_threshold_image() function
```python
# Source: cv2.adaptiveThreshold — https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html
#         PIL Image.fromarray — https://pillow.readthedocs.io/en/stable/reference/Image.html
import cv2
import numpy as np
from PIL import Image

ADAPTIVE_BLOCK_SIZE = 51   # odd integer >= 3; at 300 DPI ≈ 4.3mm neighbourhood
ADAPTIVE_C = 10            # subtracted from local Gaussian mean; positive = raise threshold

def adaptive_threshold_image(
    image: Image.Image,
    block_size: int = ADAPTIVE_BLOCK_SIZE,
    c: int = ADAPTIVE_C,
) -> Image.Image:
    gray = np.array(image.convert('L'))   # uint8, shape (H, W) — required by adaptiveThreshold
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c,
    )
    return Image.fromarray(binary, 'L')
```

### cv2.adaptiveThreshold full signature (OpenCV 4.x)
```python
# dst = cv2.adaptiveThreshold(src, maxValue, adaptiveMethod, thresholdType, blockSize, C)
#
# src:            Input grayscale image (CV_8UC1 / uint8 single-channel numpy array)
# maxValue:       Value assigned to pixels above the threshold (typically 255)
# adaptiveMethod: cv2.ADAPTIVE_THRESH_GAUSSIAN_C — Gaussian-weighted local mean
#                 cv2.ADAPTIVE_THRESH_MEAN_C — simple local mean (not used here)
# thresholdType:  cv2.THRESH_BINARY — pixels above (local_mean - C) become maxValue
#                 cv2.THRESH_BINARY_INV — inverted (NOT used: project uses THRESH_BINARY)
# blockSize:      Size of the neighbourhood square (pixels); MUST be ODD and >= 3
# C:              Constant subtracted from the local mean; positive = higher threshold
#
# Returns: dst — binary uint8 numpy array, same shape as src

binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 10)
```

### Conditional call inside process_tiff()
```python
# After deskew block, before detect_crop_box() — inside process_tiff()
        # Adaptive threshold step (PREP-04 / PREP-05: opt-in only)
        if adaptive_threshold:
            img = adaptive_threshold_image(img)
```

### argparse flag declaration
```python
# Source: https://docs.python.org/3/library/argparse.html — action='store_true'
# Matches the existing --force and --validate-only flag pattern in main()
parser.add_argument(
    '--adaptive-threshold',
    action='store_true',
    help='Apply adaptive Gaussian thresholding before OCR (improves results on scans '
         'with uneven illumination; off by default)',
)
# argparse maps --adaptive-threshold → args.adaptive_threshold (hyphens → underscores)
```

### run_batch() signature extension
```python
def run_batch(
    tiff_files: list,
    output_dir: Path,
    workers: int,
    lang: str,
    psm: int,
    padding: int,
    force: bool,
    adaptive_threshold: bool,   # NEW
) -> tuple:
    ...
    futures = {
        executor.submit(
            process_tiff, tiff_path, output_dir, lang, psm, padding, False, adaptive_threshold
        ): tiff_path
        for tiff_path in to_process
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global Otsu threshold for binarization | Adaptive Gaussian threshold for uneven illumination | N/A — both are current; Otsu remains for crop detection | Adaptive threshold is used selectively for OCR quality improvement, not as a replacement for Otsu |
| Hard-coded binarization, no opt-out | Opt-in via CLI flag | PREP-05 introduces opt-in pattern | Backward compatible: existing runs unaffected |
| `cv2.THRESH_BINARY_INV` for page/border detection | `cv2.THRESH_BINARY` (project decision in STATE.md) | Phase 1-3 decision | `THRESH_BINARY` must also be used for adaptive threshold on this corpus |

**Not deprecated:** `cv2.adaptiveThreshold()` is a stable OpenCV function with no deprecation notices as of OpenCV 4.x. The Python bindings are unchanged.

---

## Open Questions

1. **What are the correct ADAPTIVE_BLOCK_SIZE and ADAPTIVE_C values for the Zeitschriften corpus?**
   - What we know: Research consensus: block_size=11 is the smallest practical value for documents; block_size=51 is a reasonable starting point for 300 DPI; C=2 is the documentation default; C=10 is a more aggressive value for high-contrast background suppression.
   - What's unclear: The actual resolution distribution and illumination characteristics of the Zeitschriften corpus. Higher-resolution scans (400-600 DPI) may need larger block sizes (e.g., 71 or 101) to cover the same physical area.
   - Recommendation: Set `ADAPTIVE_BLOCK_SIZE = 51` and `ADAPTIVE_C = 10` as named constants in the plan. The PLAN must include a mandatory tuning step: run with `--adaptive-threshold` on a sample of 5–10 real scans from the corpus and compare word count and visual output before declaring the defaults correct. The planner should add this as an explicit verification task.
   - Confidence: LOW for the specific values — they are informed starting points, not validated defaults.

2. **Should adaptive threshold run before or after detect_crop_box()?**
   - What we know: The pipeline order is currently load → deskew → crop → OCR. Adaptive threshold is a binarization step. Running it before crop means crop detection receives a binary image (cleaner edges, potentially better contour detection). Running it after crop means the cropped region is thresholded (smaller area, less context, but the exact image sent to Tesseract is thresholded).
   - What's unclear: Which ordering produces better OCR quality on real scans. The crop step uses `cv2.THRESH_BINARY + cv2.THRESH_OTSU` internally — it re-thresholds the image regardless. Running adaptive threshold before crop is safe (Otsu on a binary input still works), but may not be necessary.
   - Recommendation: Run adaptive threshold BEFORE detect_crop_box() (i.e., the whole deskewed image is thresholded). This is the more common pattern in OCR preprocessing pipelines. Monitor `crop fallback` warning frequency when `--adaptive-threshold` is used. If crop quality degrades, move the threshold step to after the crop call.
   - Confidence: MEDIUM — logical reasoning from the pipeline structure; no empirical evidence from this specific corpus.

3. **Does cv2.adaptiveThreshold handle multipage TIFFs or unusual bit depths?**
   - What we know: `adaptive_threshold_image()` calls `image.convert('L')` first, which normalizes any mode (RGB, RGBA, palette, 16-bit) to uint8 grayscale. `cv2.adaptiveThreshold()` requires uint8. The conversion chain is safe.
   - What's unclear: 16-bit grayscale TIFFs (uint16) — PIL `convert('L')` on a 16-bit PIL image scales to 8-bit correctly.
   - Recommendation: The `image.convert('L')` pattern used in `deskew_image()` and `detect_crop_box()` is the established project pattern for mode normalization. Follow the same pattern; no additional handling needed.
   - Confidence: HIGH — this is the existing project pattern, verified in pipeline.py.

---

## Sources

### Primary (HIGH confidence)
- [OpenCV Image Thresholding tutorial (4.x)](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html) — `cv2.adaptiveThreshold()` function signature, parameter descriptions, `ADAPTIVE_THRESH_GAUSSIAN_C` method, code examples with blockSize=11, C=2. Confirmed via WebSearch result summaries (direct fetch returned 403).
- [Python argparse docs](https://docs.python.org/3/library/argparse.html) — `action='store_true'` stores True when flag present, False otherwise; `--adaptive-threshold` maps to `args.adaptive_threshold`. Verified via WebSearch result summaries.
- [Pillow Image module docs](https://pillow.readthedocs.io/en/stable/reference/Image.html) — `Image.fromarray(array, 'L')` converts uint8 2D numpy array to PIL 'L' mode image. Verified via WebSearch result summaries.
- `pipeline.py` (codebase) — existing `no_crop: bool` threading pattern through `process_tiff()` / `run_batch()` / `executor.submit()`; existing `action='store_true'` flags (`--force`, `--validate-only`); existing `THRESH_BINARY` decision; existing `image.convert('L')` and numpy conversion patterns.

### Secondary (MEDIUM confidence)
- [PyImageSearch — Adaptive Thresholding with OpenCV](https://pyimagesearch.com/2021/05/12/adaptive-thresholding-with-opencv-cv2-adaptivethreshold/) — blockSize=11 is the tutorial default; Gaussian method preferred over Mean for OCR preprocessing. Verified by consistent mention in multiple search results; source is a well-known authoritative CV blog.
- [OpenCV blog — Image Thresholding using OpenCV](https://opencv.org/blog/image-thresholding-using-opencv/) — confirms blockSize between 11 and 21 for most document binarization tasks as starting points. Cross-referenced with OpenCV tutorial content.
- WebSearch consensus on block_size=11–51 for 300 DPI document scanning — consistent across GeeksforGeeks, TutorialsPoint, StackAbuse, DataScientistsDiary. Multiple sources agree; no single authoritative citation.

### Tertiary (LOW confidence)
- WebSearch on blockSize=51, C=10 as defaults for high-DPI archival scanning — these values are informed starting points derived from reasoning about DPI and character size, not from a peer-reviewed source or empirical validation on this specific corpus. **Require validation against real Zeitschriften scans before committing.**

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already in requirements.txt; `cv2.adaptiveThreshold` is a stable, well-documented function; no new installs required.
- Architecture: HIGH — the pattern is a direct parallel to `deskew_image()` (Phase 4) and `no_crop` threading (Phase 2). The function structure, PIL↔numpy conversion, and argparse wiring are all established project patterns.
- Default parameter values (ADAPTIVE_BLOCK_SIZE, ADAPTIVE_C): LOW — 51 and 10 are informed starting points, not empirically validated for this corpus. The planner MUST include a tuning/validation step in the plan.
- Pitfalls: HIGH — `blockSize` must-be-odd is documented by OpenCV; `THRESH_BINARY` is a project decision in STATE.md; parameter threading pitfall is logically derived from the existing codebase structure.

**Research date:** 2026-02-25
**Valid until:** 2026-08-25 (stable: OpenCV 4.x API is mature; Pillow API stable; argparse is stdlib)
