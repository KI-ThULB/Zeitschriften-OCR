# Phase 4: Deskew - Research

**Researched:** 2026-02-25
**Domain:** Document image deskew — skew angle detection and correction on archival TIFF scans using Python/OpenCV/PIL
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PREP-01 | Pipeline detects the rotation angle of each scan and corrects it before OCR; applied to every TIFF automatically | `deskew.determine_skew()` provides Hough-based angle detection; PIL `Image.rotate()` applies correction in-memory before `run_ocr()` is called |
| PREP-02 | Detected rotation angle is logged per file in the result line (e.g. `[deskew: 1.4°]`), so the operator can audit which files were corrected | Angle is a float from `determine_skew()`; formatted and appended to the existing `warnings_list` / result-line mechanism already in `process_tiff()` |
| PREP-03 | If deskew fails or produces an implausible result, the pipeline falls back to the original orientation and logs a warning; the batch does not abort | `determine_skew()` returns `None` on detection failure; a plausibility gate (reject `|angle| > 10°`) covers implausible results; both cases use the uncorrected image and append to `warnings_list` |
</phase_requirements>

---

## Summary

Deskew for this project means detecting small scan-time rotations (typically under 5°) in archival journal TIFFs and correcting them in memory before passing the image to Tesseract. The standard Python ecosystem has a well-maintained purpose-built library, `deskew` (sbrunner, v1.5.3, June 2025), that uses the Hough line transform to detect skew angles and returns a float or `None`. This covers the detection side entirely.

For the rotation side, PIL's `Image.rotate()` is the correct tool because the pipeline already works in PIL-image space. The correction is purely in-memory — the original TIFF is never modified, and the rotated image is fed directly to `run_ocr()` exactly as the cropped image is today.

The two open questions from `STATE.md` both have clear answers after research. Algorithm choice: the `deskew` library uses Hough transform, which is more robust than projection-profile for images with mixed content (illustrations, column rules, borders) and does not require an iterative angle sweep. Plausibility threshold: a `|angle| > 10°` reject gate is the appropriate safeguard for archival periodicals, because genuine scanner skew is almost always under 5° and angles above 10° almost always indicate a misdetection on a decorative border or illustration.

**Primary recommendation:** Add `deskew>=1.5.0` to `requirements.txt`. Implement `deskew_image()` as a pure function that takes a PIL Image and returns `(PIL Image, float | None, bool)` — the corrected (or original) image, the detected angle, and a `fallback_used` flag. Call it from `process_tiff()` between `load_tiff()` and the crop step, extend `warnings_list` with angle info or a warning string, and include the angle in the per-file result line.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `deskew` | >=1.5.0 (latest: 1.5.3, 2025-06-27) | Hough-transform-based skew angle detection | Purpose-built for document skew; production-used; returns `None` on failure; tunable via `min_angle`/`max_angle`/`num_peaks`; MIT license |
| `Pillow` | >=11.1.0 (already in requirements.txt) | In-memory image rotation via `Image.rotate()` | Already a project dependency; `rotate(angle, expand=True, fillcolor=255, resample=Image.BICUBIC)` is the correct call |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | transitive via `deskew` / `opencv-python-headless` | Grayscale array conversion for `determine_skew()` | Required as input format: `np.array(img.convert('L'))` |
| `scikit-image` | transitive via `deskew` | Hough transform internals in `deskew` library | Installed automatically as a `deskew` dependency; not called directly |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `deskew` library | OpenCV `cv2.minAreaRect` on dilated text contours | More code to maintain; `minAreaRect` returns angle in `[-90, 0)` requiring manual normalization; less robust on sparse-text pages like illustrated spreads |
| `deskew` library | Projection-profile sweep (DRT / Radon transform) | Iterative sweep over angle range; slower; limited to ~±10° unless you widen the sweep; overkill given `deskew` already solves this |
| `PIL.Image.rotate()` | `cv2.warpAffine()` | Would require round-tripping through numpy; PIL is already the working image type in `process_tiff()` |

**Installation:**
```bash
pip install "deskew>=1.5.0"
```

Add to `requirements.txt`:
```
deskew>=1.5.0
```

Note: `deskew` pulls in `scikit-image` and `numpy`. Both are compatible with the existing stack.

---

## Architecture Patterns

### Recommended Project Structure

No new files needed. All deskew logic lives in `pipeline.py` as a single new function:

```
pipeline.py
├── load_tiff()            → (PIL Image, dpi, warnings)
├── deskew_image()         → (PIL Image, float | None, bool)   ← NEW in Phase 4
├── detect_crop_box()      → (crop box, fallback_used)
├── run_ocr()              → ALTO XML bytes
├── build_alto21()         → ALTO XML bytes
├── count_words()          → int
└── process_tiff()         → calls deskew_image() after load_tiff()
```

### Pattern 1: deskew_image() as a pure function

**What:** A self-contained function that wraps `determine_skew()` and `Image.rotate()`, always returns a valid PIL Image (original on failure), and surfaces the angle + fallback flag to the caller.

**When to use:** Called from `process_tiff()` after `load_tiff()`, before `detect_crop_box()`. The caller appends to `warnings_list` based on the returned angle/fallback.

**Example:**
```python
# Source: deskew PyPI docs (https://pypi.org/project/deskew/) +
#         PIL docs (https://pillow.readthedocs.io/en/stable/reference/Image.html)
from deskew import determine_skew
import numpy as np
from PIL import Image

DESKEW_MAX_ANGLE = 10.0   # degrees — reject corrections above this as implausible

def deskew_image(
    image: Image.Image,
    max_angle: float = DESKEW_MAX_ANGLE,
) -> tuple[Image.Image, 'float | None', bool]:
    """Detect and correct scan skew using Hough line transform.

    Args:
        image: PIL Image of the scan (any mode; converted to grayscale internally)
        max_angle: Maximum plausible correction angle in degrees (default: 10.0).
                   Angles above this are treated as detection failures.

    Returns:
        corrected: PIL Image — rotated if angle is plausible, original otherwise
        angle: Detected angle in degrees (float), or None if detection failed
        fallback_used: True if original image is returned (detection failed OR
                       angle exceeded max_angle)
    """
    # determine_skew() requires a grayscale numpy array
    gray = np.array(image.convert('L'))

    try:
        angle = determine_skew(gray)
    except Exception:
        # Library raised unexpectedly — treat as detection failure
        return image, None, True

    # Case 1: detection returned None (no dominant angle found)
    if angle is None:
        return image, None, True

    # Case 2: angle is implausible (likely misdetection on border/illustration)
    if abs(angle) > max_angle:
        return image, angle, True

    # Case 3: angle is zero or near-zero — skip rotation to avoid resampling artifact
    if abs(angle) < 0.05:
        return image, angle, False

    # Case 4: apply correction
    # expand=True avoids cropping content; fillcolor=255 fills corners with white
    # (archival scans: dark scanner bed, light page — white is the correct fill)
    # resample=Image.BICUBIC preserves text sharpness better than BILINEAR
    corrected = image.rotate(
        angle,
        expand=True,
        fillcolor=255,
        resample=Image.Resampling.BICUBIC,
    )
    return corrected, angle, False
```

### Pattern 2: Integration in process_tiff()

**What:** `deskew_image()` is inserted as a single step between `load_tiff()` and `detect_crop_box()`. The angle and fallback status are appended to `warnings_list`. The per-file result line already has a `warn_str` suffix — the deskew annotation uses the same mechanism.

**When to use:** Always in Phase 4. Deskew is unconditional (PREP-01: "applied to every TIFF automatically").

**Example:**
```python
# Inside process_tiff() — after load_tiff(), before detect_crop_box()

# Deskew step (PREP-01)
img, deskew_angle, deskew_fallback = deskew_image(img)

if deskew_fallback:
    if deskew_angle is None:
        warnings_list.append('deskew: detection failed, using original orientation')
    else:
        # angle was detected but implausible
        warnings_list.append(
            f'deskew: implausible angle {deskew_angle:.1f}°, using original orientation'
        )
else:
    # PREP-02: report angle in result line
    # Format: [deskew: 1.4°] — zero-degree scans show [deskew: 0.0°]
    warnings_list.append(f'deskew: {deskew_angle:.1f}°')
```

Note: The existing `warn_str` construction in `process_tiff()` already wraps `warnings_list` in `[WARN: ...]`. For deskew, the angle info should appear unconditionally (it is diagnostic, not a warning). This requires separating the "deskew annotation" from the "warning" list, or using a dedicated prefix. See Anti-Patterns below.

### Pattern 3: Result line format

PREP-02 specifies: `[deskew: 1.4°]`. The existing result line is:
```
scan_001.tif → output/alto/scan_001.xml (11.1s, 46 words) [WARN: no DPI tag, using 300]
```

Target with deskew:
```
scan_001.tif → output/alto/scan_001.xml (11.1s, 46 words) [deskew: 1.4°]
scan_001.tif → output/alto/scan_001.xml (11.1s, 46 words) [deskew: 0.0°] [WARN: no DPI tag]
scan_001.tif → output/alto/scan_001.xml (11.1s, 46 words) [WARN: deskew detection failed]
```

The cleanest implementation: maintain a `deskew_str` separate from `warnings_list`, and build the result line suffix from both.

### Anti-Patterns to Avoid

- **Applying deskew after crop:** The crop step uses contour detection on the full image. Deskewing first ensures the page contour is axis-aligned, making crop detection more reliable. Always: deskew → crop → OCR.
- **Rotating the original TIFF on disk:** REQUIREMENTS.md explicitly lists "Saving preprocessed images as deliverables" as out of scope. The rotation is in-memory only; `load_tiff()` re-reads the original file if reprocessed.
- **Using `expand=False`:** Without expand, rotation crops corners. For text near page edges (archival journals often have tight margins), this silently loses content that will then be absent from the ALTO XML.
- **Not handling `None` from `determine_skew()`:** The library explicitly documents that `None` is a valid return. Any code path that calls `image.rotate(None, ...)` will raise `TypeError`. The fallback must check before rotating.
- **Using a fixed `fillcolor` without checking image mode:** A grayscale image ('L' mode) needs `fillcolor=255` (white). An RGB image needs `fillcolor=(255, 255, 255)`. PIL's `rotate()` accepts an integer for 'L' mode and a tuple for 'RGB'. Load archival TIFFs via `load_tiff()` which returns a PIL Image in whatever mode the file uses — apply `convert('RGB')` before rotate if mode is uncertain, or handle both.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hough-line angle detection | Custom `cv2.HoughLinesP` + angle histogram | `deskew.determine_skew()` | Handles edge detection, peak finding, angle normalization, and `None`-on-failure; 20+ edge cases already solved |
| Projection-profile sweep | Iterative DRT / rotate-and-score loop | `deskew.determine_skew()` | Slower, more code, needs manual angle range and step size tuning; `deskew` already beats it for document use cases |
| Skew angle plausibility | Custom statistical outlier detection | Simple `abs(angle) > threshold` gate | The plausibility problem here is domain-specific (archival scans rarely exceed 5°), not a statistical problem; a hard threshold is correct and explicit |

**Key insight:** `deskew` 1.5.3 was released 2025-06-27 and is actively maintained. It solves exactly the document skew detection problem and has a dependency chain (scikit-image, numpy) that is already present transitively in this project's OpenCV installation. There is no reason to implement detection from scratch.

---

## Common Pitfalls

### Pitfall 1: `determine_skew()` returns `None` and code crashes

**What goes wrong:** `image.rotate(None, ...)` raises `TypeError` at runtime; the worker raises in `ProcessPoolExecutor`, gets collected as a failed file.
**Why it happens:** Callers assume `determine_skew()` always returns a float. The library documents `None` as the no-detection return but many tutorials omit the guard.
**How to avoid:** Always check `if angle is None` before calling `rotate()`. Return the original image unchanged.
**Warning signs:** `TypeError: argument of type 'NoneType' is not iterable` in the JSONL error log.

### Pitfall 2: Implausible angle applied without gate

**What goes wrong:** A large illustration or decorative border dominates the Hough space; `determine_skew()` returns 45° or -45°; the image is rotated 45° before OCR; Tesseract produces near-zero word count; ALTO file has no content.
**Why it happens:** Hough transform finds the dominant straight-line angle in the image — on a page with a heavy ruled border or full-page illustration, that angle may not reflect text orientation.
**How to avoid:** Reject corrections where `abs(angle) > 10.0` and fall back to original orientation with a warning. The 10° threshold is appropriate for archival periodicals where genuine skew is almost always under 5°. Document the threshold as a named constant `DESKEW_MAX_ANGLE = 10.0` so it can be tuned.
**Warning signs:** Result lines showing `[deskew: 45.0°]` or `[deskew: -45.0°]`; word count drops to near zero.

### Pitfall 3: `expand=False` silently clips page margins

**What goes wrong:** Rotation without canvas expansion clips image corners. Text near the edges (journal headers, footers, page numbers) is permanently lost for the OCR step. The ALTO XML contains fewer words than the original page, with no warning.
**Why it happens:** Default `expand` is `False` in PIL. A 2° rotation of a 3000×4000 image clips about 70px at each corner — not enough to notice visually but enough to miss a running header.
**How to avoid:** Always pass `expand=True`. The expanded canvas is slightly larger than the original but is discarded after OCR (not saved to disk).
**Warning signs:** Word count slightly lower than expected for straight pages; content missing from ALTO in corner regions.

### Pitfall 4: Fill color wrong for image mode

**What goes wrong:** Rotating an 'L' (grayscale) PIL Image with `fillcolor=(255, 255, 255)` (a tuple) raises `TypeError`. Rotating an 'RGB' image with `fillcolor=255` (an integer) may produce unexpected behavior.
**Why it happens:** PIL `rotate()` fill color must match the image mode.
**How to avoid:** Use `fillcolor=255` for grayscale ('L') images. For safety, call `image.convert('RGB')` before rotate and use `fillcolor=(255, 255, 255)`, or detect `image.mode` explicitly. Archival TIFFs from flatbed scanners are often 'L' or 'RGB' — not consistent.
**Warning signs:** `TypeError` in error log referencing `rotate()`.

### Pitfall 5: Deskewing after crop destroys reliability

**What goes wrong:** If crop detection runs before deskew, the detected crop box is computed on a skewed image. After rotation, the crop box no longer aligns with the actual page boundaries.
**Why it happens:** Step order mistake — easy to do because crop is the first step after load in the existing pipeline.
**How to avoid:** Insert deskew between `load_tiff()` and `detect_crop_box()`. The correct order is: load → deskew → crop → OCR.
**Warning signs:** `crop fallback, using full image` warnings appearing more often after introducing deskew; coordinate violations in ALTO validation.

### Pitfall 6: Zero-degree rotation causes resampling artifact

**What goes wrong:** Applying `Image.rotate(0.0, resample=BICUBIC, expand=True)` on a perfectly straight image introduces minor resampling noise from bicubic interpolation even at 0°. This is a no-op semantically but not computationally.
**Why it happens:** PIL does not short-circuit on 0-degree rotations with non-NEAREST resampling.
**How to avoid:** Add a guard: if `abs(angle) < 0.05`, skip the rotate call and return the image unchanged. This satisfies Success Criterion 4 ("a zero-degree scan passes through without any quality degradation").
**Warning signs:** Subtle pixel-level differences in output between pre- and post-deskew runs on already-straight scans (detectable only via pixel-diff testing).

---

## Code Examples

Verified patterns from official sources:

### Minimal deskew integration (from PyPI docs + PIL docs)
```python
# Source: https://pypi.org/project/deskew/ + https://pillow.readthedocs.io/en/stable/reference/Image.html
from deskew import determine_skew
import numpy as np
from PIL import Image

grayscale = np.array(image.convert('L'))
angle = determine_skew(grayscale)   # Returns float or None

if angle is not None and abs(angle) <= 10.0 and abs(angle) >= 0.05:
    corrected = image.rotate(
        angle,
        expand=True,
        fillcolor=255,
        resample=Image.Resampling.BICUBIC,
    )
else:
    corrected = image  # passthrough — original unchanged
```

### Handling grayscale vs RGB fill color
```python
# Source: PIL documentation — Image.rotate() fillcolor parameter
mode = image.mode
fill = 255 if mode == 'L' else (255, 255, 255) if mode == 'RGB' else 255
corrected = image.rotate(angle, expand=True, fillcolor=fill, resample=Image.Resampling.BICUBIC)
```

### determine_skew with restricted angle range (optional tuning)
```python
# Source: https://pypi.org/project/deskew/ — parameters min_angle, max_angle
# Pre-filtering the search range can improve detection accuracy and speed
# on documents where extreme angles are physically impossible
from deskew import determine_skew
angle = determine_skew(gray, min_angle=-15, max_angle=15)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom Hough + manual angle histogram | `deskew` library (Hough under the hood) | ~2018 onwards | Standard library available; no hand-rolling needed |
| `cv2.warpAffine()` for rotation | `PIL.Image.rotate(expand=True)` when already in PIL space | N/A (both current) | PIL rotate is simpler and avoids numpy round-trip when image is already PIL |
| Projection profile sweep | Hough transform (via `deskew`) | `deskew` has always used Hough | Hough is preferred for mixed-content pages; projection profile is better for text-only dense pages |
| `Image.Resampling.BICUBIC` via deprecated constant `Image.BICUBIC` | `Image.Resampling.BICUBIC` | Pillow 10.0 (deprecated old constants) | Must use `Image.Resampling.BICUBIC` not `Image.BICUBIC` — the old constants still work but emit DeprecationWarning |

**Deprecated/outdated:**
- `Image.BICUBIC` (and `Image.BILINEAR`, `Image.NEAREST`): Deprecated in Pillow 10.0 in favour of `Image.Resampling.BICUBIC` etc. Use the `Resampling` enum.

---

## Open Questions

1. **What fill color should be used for multi-mode TIFFs (palette, CMYK)?**
   - What we know: Archival periodical scans are almost always 'L' (grayscale) or 'RGB'. The existing pipeline uses `image.convert('RGB')` at the crop step.
   - What's unclear: Whether `load_tiff()` returns a consistent mode across the real Zeitschriften corpus.
   - Recommendation: In `deskew_image()`, detect `image.mode` and set fill accordingly, or defensively call `image.convert('RGB')` first if mode is not 'L' or 'RGB'. Add a note in the function docstring.

2. **Is 10° the right plausibility threshold for this specific corpus?**
   - What we know: Archival scanner skew for periodicals is typically under 5°. Literature on document image processing consistently cites 10–15° as the outer bound for genuine scanner tilt. The `deskew` library clamps its default output to ±45°.
   - What's unclear: Whether the Zeitschriften scans have any edge cases (e.g., pages physically pasted at an angle, deliberate diagonal layouts).
   - Recommendation: Start with 10° as the constant `DESKEW_MAX_ANGLE`. Make it a named constant (not a magic number) so it can be adjusted without a code audit. A future CLI flag `--deskew-max-angle` could expose it if needed (out of scope for Phase 4).

3. **Does the ProcessPoolExecutor worker handle the `deskew` import correctly?**
   - What we know: Workers are forked/spawned processes on macOS (spawn context). `deskew` imports scikit-image which imports numpy at module load time. This is a module-level import, which is safe for spawned workers as long as `import deskew` is at the top of `pipeline.py` (not inside the function).
   - What's unclear: Whether there are any known spawn-context issues with scikit-image on macOS (arm64).
   - Recommendation: Place `from deskew import determine_skew` at the top-level imports of `pipeline.py`. If a spawn issue appears, the error will be a clean `ImportError` in the worker, not a silent failure.

---

## Sources

### Primary (HIGH confidence)
- [deskew PyPI page](https://pypi.org/project/deskew/) — version, algorithm, function signatures, angle range, `None` return, parameters, dependencies (scikit-image, numpy), MIT license. Verified 2026-02-25.
- [GitHub sbrunner/deskew `__init__.py`](https://github.com/sbrunner/deskew/blob/master/deskew/__init__.py) — confirmed Hough transform algorithm, `None` return on failure, all parameters including `min_angle`, `max_angle`, `num_peaks`, `sigma`, `min_deviation`.
- [Pillow Image module docs](https://pillow.readthedocs.io/en/stable/reference/Image.html) — `rotate()` signature, `expand`, `fillcolor`, `resample` parameters. `Image.Resampling.BICUBIC` is the current constant.

### Secondary (MEDIUM confidence)
- [felix.abecassis.me — OpenCV Rotation/Deskewing](https://felix.abecassis.me/2011/10/opencv-rotation-deskewing/) — describes the warpAffine + getRotationMatrix2D approach (validated as the reference implementation; confirmed our choice of PIL.rotate() is simpler for PIL-based pipelines).
- [OpenCV Hough Line Transform docs](https://docs.opencv.org/4.x/d6/d10/tutorial_py_houghlines.html) — background on Hough transform; confirms `deskew` library's approach is standard.
- [OCRmyPDF deskew documentation](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html) — confirms deskew is a pre-OCR step, distinct from cardinal rotation; uses Leptonica's Postl variance algorithm internally (different from `deskew` library but confirms the domain pattern).

### Tertiary (LOW confidence)
- WebSearch consensus on ±10° plausibility threshold — multiple sources (Medium articles, GeeksforGeeks, PyImageSearch summaries) consistently treat small-angle correction (under 10°) as the target domain for document deskew. No single authoritative source for the "10° threshold" specifically; it is an informed judgment based on the literature pattern.
- WebSearch on projection-profile vs Hough tradeoff — consistent across multiple sources that Hough is preferred for mixed-content pages; projection profile suited to text-dense pages. This supports the `deskew` library choice but the tradeoff analysis is not from a single verified source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `deskew` 1.5.3 verified on PyPI (June 2025); PIL `rotate()` verified in official Pillow docs; both are confirmed compatible with existing stack.
- Architecture: HIGH — `deskew_image()` pattern follows the existing `detect_crop_box()` pattern in the codebase exactly; integration point is unambiguous.
- Plausibility threshold (10°): MEDIUM — well-supported by domain consensus but not from a single authoritative source; named constant approach makes it adjustable.
- Pitfalls: HIGH — `None` return and `expand=True` are documented facts; fill color type mismatch is a known PIL behavior; step-order pitfall is logically derived from the existing crop implementation.

**Research date:** 2026-02-25
**Valid until:** 2026-08-25 (stable: `deskew` is a mature library; PIL API stable)
