# Phase 1: Single-File Pipeline - Research

**Researched:** 2026-02-24
**Domain:** Python image processing / OCR / XML (Pillow + OpenCV + pytesseract + lxml)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Single script: `pipeline.py` at the repo root — no package structure, no install required
- Invocation: `python pipeline.py --input <tiff> --output <dir>`
- Python 3.10+ (modern type hints, match/case available)
- Dependencies declared in `requirements.txt`
- ALTO XML filename: same stem as input TIFF, `.xml` extension — `scan_001.tif` → `scan_001.xml`
- Output placed in `<output_dir>/alto/` subfolder — e.g. `output/alto/scan_001.xml`
- `<output_dir>/alto/` is created automatically if it doesn't exist
- Successful run: one-line result to stdout: `scan_001.tif → output/alto/scan_001.xml (1.2s, 847 words)`
- Warnings (missing DPI tag, crop fallback triggered) appended inline to the result line: `... [WARN: no DPI tag, using 300]`
- Errors: message to stderr (`ERROR: scan_001.tif: <reason>`) and exit code 1 — no Python traceback by default
- `--padding PX` CLI flag to set margin around detected content area (default: 50px)
- `--no-crop` flag to bypass OpenCV detection entirely and use original TIFF bounds
- Fallback thresholds (40% / 98%) hardcoded in Phase 1; not yet exposed as flags

### Claude's Discretion
- Exact contour detection parameters (Otsu threshold settings, erosion/dilation pre-processing)
- ALTO 2.1 internal structure (MeasurementUnit, Layout/Page element nesting)
- How to handle multi-page TIFFs (if any exist — treat as single-page or error)
- Temp file handling for pytesseract I/O

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within Phase 1 scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PIPE-01 | Load each TIFF with Pillow lazy loading; extract DPI from TIFF metadata; default to 300 DPI with warning if absent | Verified: `image.info.get('dpi')` returns None when tag absent; fallback pattern confirmed |
| PIPE-02 | Detect scan border via OpenCV contour analysis; configurable padding (default 50px); fallback to original bounds if detected area < 40% or > 98%; log fallback | Verified: THRESH_BINARY (not INV) correct for dark-border/white-page scans; fallback ratio calculation pattern confirmed |
| PIPE-03 | Run Tesseract 5.x (LSTM) on cropped image; configurable language (default `deu`) and `--psm` | Verified: tesseract 5.5.1 installed; `deu` language pack present; `--dpi` config flag works |
| PIPE-04 | Produce schema-valid ALTO 2.1 XML per TIFF; correct namespace; word coordinates offset by crop box | CRITICAL FINDING: Two valid ALTO 2.1 namespaces — see Namespace Decision below |
</phase_requirements>

---

## Summary

Phase 1 builds the core single-file pipeline: TIFF load → border crop → OCR → ALTO 2.1 XML output. All five required libraries are already installed in the project Python environment (Pillow 11.1.0, opencv-python 4.11.0, pytesseract 0.3.13, lxml 5.3.0). Tesseract 5.5.1 is installed with the `deu` language pack available. No new dependencies need to be installed before coding begins.

The most important Phase 1 discoveries from hands-on verification: (1) Tesseract outputs ALTO with `MeasurementUnit=pixel` and namespace `http://www.loc.gov/standards/alto/ns-v3#` — both must be rewritten for ALTO 2.1 compliance. (2) The correct threshold mode for archival scan border detection is `THRESH_BINARY` (not `THRESH_BINARY_INV` as shown in STACK.md) — the content area is the lighter region, not the darker border. (3) The ALTO 2.1 namespace situation has a critical ambiguity: the LOC official XSD uses `http://www.loc.gov/standards/alto/ns-v2#`, but the historically common Goobi-era namespace is `http://schema.ccs-gmbh.com/ALTO`. Both are schema-valid under their respective XSDs.

The coordinate offset (HPOS += crop_x, VPOS += crop_y) is the single most correctness-critical operation in the ALTOBuilder. Since originals are never replaced, Goobi will display the original TIFF and ALTO coordinates must align with it, not the cropped intermediate.

**Primary recommendation:** Build pipeline.py as five focused functions (one per component), apply crop offset to ALL positional elements (Page, PrintSpace, ComposedBlock, TextBlock, TextLine, String, SP), and default `MeasurementUnit` to `pixel` (Tesseract's native unit — no DPI conversion required).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 11.1.0 (installed) | TIFF I/O, lazy loading, DPI extraction | Only Python image library with lazy TIFF loading and DPI metadata preservation |
| opencv-python | 4.11.0 (installed) | Grayscale + threshold + contour detection for crop box | Standard CV library for contour-based document border detection |
| pytesseract | 0.3.13 (installed) | Run Tesseract OCR, emit ALTO XML string | Direct wrapper for Tesseract ALTO output mode |
| lxml | 5.3.0 (installed) | Parse/rewrite Tesseract ALTO → ALTO 2.1; XSD validation | Best Python XML library for namespace rewriting and schema validation |
| argparse | stdlib | CLI flag parsing | No extra dependency; sufficient for Phase 1 flag surface |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib | stdlib | Path manipulation (stem, mkdir, etc.) | All file path operations |
| time | stdlib | Measure processing duration for output line | Wrap `process_tiff()` call |
| sys | stdlib | Write to stderr, exit with code 1 | Error path only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytesseract ALTO output | pytesseract TSV + manual ALTO build | TSV approach guarantees ALTO 2.1 structure but requires building all XML manually; use if namespace issues prove intractable |
| opencv-python | opencv-python-headless | headless is preferred for servers; opencv-python is already installed and works identically on macOS; defer swap to Phase 2 |
| `MeasurementUnit=pixel` | `MeasurementUnit=mm10` | pixel avoids DPI-based conversion math and is valid per ALTO 2.1 XSD; mm10 required only if target Goobi instance mandates it (see Open Questions) |

**Installation:** All libraries already installed. No action required.

```bash
# requirements.txt — declare these versions for reproducibility
Pillow>=11.1.0
opencv-python-headless>=4.9.0
pytesseract>=0.3.13
lxml>=5.3.0
```

System deps already present: tesseract 5.5.1 with `deu` language pack at `/opt/homebrew/share/tessdata/`.

---

## Architecture Patterns

### Recommended Project Structure
```
Zeitschriften-OCR/
├── pipeline.py          # single script — all five components as functions
├── requirements.txt     # pinned versions
└── output/
    └── alto/
        ├── scan_001.xml
        └── scan_002.xml
```

### Pattern 1: Five-Function Pipeline
**What:** One Python function per logical component, called in sequence from `process_tiff()`. No classes in Phase 1 — functions with explicit parameters are simpler and easier to test manually.
**When to use:** Single-file script without install; complexity is low enough that classes add ceremony without benefit.

```python
# Verified interface pattern from ARCHITECTURE.md
import argparse, sys, time
from pathlib import Path
from PIL import Image
import cv2, numpy as np, pytesseract
from lxml import etree

def load_tiff(path: Path) -> tuple[Image.Image, tuple[float, float]]:
    """Returns (image, (dpi_x, dpi_y)).
    Falls back to (300.0, 300.0) if DPI tag absent — logs WARN."""
    img = Image.open(path)
    dpi = img.info.get('dpi')
    warned = False
    if dpi is None:
        dpi = (300.0, 300.0)
        warned = True
    return img, dpi, warned  # extend tuple with warn flag

def detect_crop_box(
    image: Image.Image,
    padding: int = 50,
    min_ratio: float = 0.40,
    max_ratio: float = 0.98,
) -> tuple[tuple[int,int,int,int], bool]:
    """Returns ((left, upper, right, lower), fallback_used).
    Uses THRESH_BINARY to find light page area against dark scanner bed."""
    img_w, img_h = image.size
    orig_area = img_w * img_h
    img_array = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    # THRESH_BINARY: light page content becomes white, dark border becomes black
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    fallback = True
    box = (0, 0, img_w, img_h)
    if contours:
        x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
        ratio = (w * h) / orig_area
        if min_ratio <= ratio <= max_ratio:
            left = max(0, x - padding)
            upper = max(0, y - padding)
            right = min(img_w, x + w + padding)
            lower = min(img_h, y + h + padding)
            box = (left, upper, right, lower)
            fallback = False
    return box, fallback

def run_ocr(image: Image.Image, lang: str, psm: int, dpi: int) -> str:
    """Returns raw ALTO XML string from Tesseract."""
    config = f'--psm {psm} --dpi {dpi}'
    return pytesseract.image_to_alto_xml(image, lang=lang, config=config)

def build_alto21(
    alto_xml: str | bytes,
    crop_box: tuple[int,int,int,int],
) -> bytes:
    """Rewrites Tesseract ALTO 3.x → ALTO 2.1 namespace.
    Applies crop offset to all positional elements.
    Returns UTF-8 bytes ready to write."""

def process_tiff(
    tiff_path: Path,
    output_dir: Path,
    lang: str,
    psm: int,
    padding: int,
    no_crop: bool,
) -> str:
    """Returns one-line result string for stdout."""
```

### Pattern 2: Namespace Rewrite via String Replace + lxml Round-Trip
**What:** Parse Tesseract ALTO bytes with lxml, serialize to string, replace old namespace URI with new one, re-parse. This is the simplest reliable approach for a full-document namespace swap in lxml (lxml does not support in-place nsmap mutation).
**When to use:** Always for the ALTO 3.x → 2.1 rewrite.

```python
# Source: verified against live tesseract 5.5.1 + lxml 5.3.0 output
ALTO3_NS = 'http://www.loc.gov/standards/alto/ns-v3#'
ALTO21_NS = 'http://schema.ccs-gmbh.com/ALTO'  # see Namespace Decision below

def rewrite_alto_namespace(alto_bytes: bytes, old_ns: str, new_ns: str) -> etree._Element:
    root = etree.fromstring(alto_bytes)
    xml_str = etree.tostring(root, encoding='unicode')
    xml_str = xml_str.replace(old_ns, new_ns)
    return etree.fromstring(xml_str.encode())
```

### Pattern 3: Crop Offset — All Positional Elements
**What:** After namespace rewrite, iterate ALL elements and increment HPOS/VPOS by crop_x/crop_y. The offset must be applied before writing — NOT after validation.
**When to use:** Whenever `--no-crop` is NOT used AND crop box differs from full image bounds.

```python
# Source: verified against lxml 5.3.0 element iteration
POSITIONAL_TAGS = {'String', 'SP', 'TextLine', 'TextBlock', 'ComposedBlock',
                   'PrintSpace', 'Illustration', 'GraphicalElement', 'ComposedBlock'}

def apply_crop_offset(root: etree._Element, crop_x: int, crop_y: int, namespace: str) -> None:
    """Mutates root in-place. crop_x = box[0], crop_y = box[1]."""
    ns_prefix = '{' + namespace + '}'
    for elem in root.iter():
        local = elem.tag.replace(ns_prefix, '') if ns_prefix in elem.tag else elem.tag
        if local in POSITIONAL_TAGS:
            if 'HPOS' in elem.attrib:
                elem.attrib['HPOS'] = str(int(elem.attrib['HPOS']) + crop_x)
            if 'VPOS' in elem.attrib:
                elem.attrib['VPOS'] = str(int(elem.attrib['VPOS']) + crop_y)
```

### Pattern 4: Output Line Format
**What:** All feedback on one line to stdout; warnings inline; errors to stderr + exit 1.
**When to use:** Phase 1 CLI output contract.

```python
# Successful run
print(f"{tiff_path.name} → {output_path} ({elapsed:.1f}s, {word_count} words)")
# With warnings
print(f"{tiff_path.name} → {output_path} ({elapsed:.1f}s, {word_count} words) [WARN: no DPI tag, using 300]")
# Error path
print(f"ERROR: {tiff_path.name}: {reason}", file=sys.stderr)
sys.exit(1)
```

### Anti-Patterns to Avoid
- **Using THRESH_BINARY_INV for border detection:** INV makes dark content white. For archival scans (dark scanner bed, light page), THRESH_BINARY is correct — it makes the light page content white. THRESH_BINARY_INV will detect the entire image as one contour.
- **Applying crop offset to width/height attributes:** WIDTH and HEIGHT are dimensions, not positions. Only HPOS and VPOS need the offset. Mutating WIDTH/HEIGHT breaks the element geometry.
- **Using cv2.imread() for TIFF loading:** Loads full decompressed array immediately (no lazy loading), discards DPI metadata. Use `Image.open()` instead and convert to numpy only for crop detection.
- **Passing numpy array to pytesseract:** Pass the PIL Image directly; pytesseract writes a temp PNG internally. Passing numpy arrays can cause color-channel confusion (RGB vs BGR).
- **Rewriting namespace after applying offset:** Apply offset BEFORE namespace rewrite — or apply offset using the pre-rewrite namespace. The namespace affects the `{ns}TagName` format used in `elem.tag`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ALTO XML structure | Custom XML serializer | pytesseract ALTO output | Tesseract handles block/line/word hierarchy, confidence scores, IDs |
| XML schema validation | Custom attribute checks | `lxml.etree.XMLSchema` | Handles full XSD 1.0 validation including type constraints, cardinality |
| Contour-based crop | Custom edge detector | `cv2.findContours` + `cv2.boundingRect` | Handles multi-contour images, arbitrary shapes, subpixel precision |
| Temp file for Tesseract | Custom tempfile + cleanup | pytesseract (internal) | pytesseract handles tempfile creation/deletion safely |
| DPI-aware coordinate conversion | Custom px→mm formula | Keep `MeasurementUnit=pixel` | Eliminates DPI conversion entirely; ALTO 2.1 XSD allows pixel units |

**Key insight:** Tesseract + pytesseract already produce valid ALTO structure with correct block/line/word nesting. The only required post-processing is namespace rewrite and coordinate offset. Building ALTO from TSV is a fallback path only.

---

## Critical Finding: ALTO 2.1 Namespace Decision

**Confidence:** MEDIUM (requires project-specific confirmation)

There are two different "ALTO 2.1" namespaces in active use:

| Namespace URI | Origin | XSD validates? | Goobi era |
|---------------|--------|----------------|-----------|
| `http://schema.ccs-gmbh.com/ALTO` | Original CCS GmbH ALTO 1.x/2.0 | Against CCS XSD | Older Goobi/Kitodo installations |
| `http://www.loc.gov/standards/alto/ns-v2#` | LOC-maintained ALTO 2.0/2.1 | Against LOC XSD (verified valid) | Newer installations, DFG Viewer |

**Verified:** The LOC official ALTO 2.1 XSD at `http://www.loc.gov/standards/alto/alto.xsd` has `targetNamespace="http://www.loc.gov/standards/alto/ns-v2#"`. A minimal ALTO document using `ns-v2` validates correctly against this schema.

**The CCS-GmbH namespace** (`http://schema.ccs-gmbh.com/ALTO`) was named in CONTEXT.md as the target. This is the historically common namespace used in older Goobi/intranda workflows. It is a valid choice when the target Goobi instance expects it.

**Recommendation for Phase 1:** Use the CCS-GmbH namespace as specified in CONTEXT.md, since this was explicitly decided by the user. Note that `MeasurementUnit=pixel` is valid under both namespaces per the ALTO 2.1 XSD spec. Mark in STATE.md that the Goobi operator must confirm which namespace their instance expects before Phase 1 is considered production-ready.

**Namespace rewrite target:** `xmlns="http://www.loc.gov/standards/alto/ns-v3#"` → `xmlns="http://schema.ccs-gmbh.com/ALTO"` (also remove `xsi:schemaLocation` pointing to alto-3-0.xsd).

---

## Common Pitfalls

### Pitfall 1: Wrong Threshold Direction for Scan Border Detection
**What goes wrong:** Using `THRESH_BINARY_INV + THRESH_OTSU` (as shown in STACK.md) when the scanner bed is darker than the page content returns the full image as one contour — no crop is detected.
**Why it happens:** THRESH_BINARY_INV makes dark pixels white; for scan images with dark borders and white pages, the border (small area) is detected, not the content area. The largest contour becomes the full image.
**How to avoid:** Use `THRESH_BINARY + THRESH_OTSU` — this makes the light page content white and finds it as the largest contour.
**Warning signs:** Area ratio = 1.00 on every image (fallback always triggers or no crop applied).

### Pitfall 2: Tesseract DPI Assumption (Defaults to 70 DPI)
**What goes wrong:** When no DPI is passed to Tesseract, it internally assumes 70 DPI. The ALTO pixel coordinates may appear correct but coordinate-to-physical-dimension mapping becomes wrong in Goobi.
**Why it happens:** pytesseract passes the image as a PNG temp file with no embedded DPI metadata; Tesseract then assumes 70 DPI for its internal page layout analysis.
**How to avoid:** Always pass `--dpi {int(dpi_x)}` in the pytesseract config string, using the DPI extracted from the TIFF (or the 300 DPI fallback). Since `MeasurementUnit=pixel`, the ALTO coordinates stay in pixels regardless — but Tesseract's line segmentation quality benefits from knowing the real DPI.
**Warning signs:** Poor word segmentation on high-DPI scans (>300 DPI); words run together or over-segmented.

### Pitfall 3: HPOS/VPOS Offset Applied to WIDTH/HEIGHT
**What goes wrong:** Accidentally incrementing WIDTH and HEIGHT attributes during the offset loop corrupts element geometry (boxes become too large).
**Why it happens:** Iterating over all attributes and applying offset to any numeric attribute, rather than specifically targeting HPOS and VPOS.
**How to avoid:** The offset function must explicitly check `if 'HPOS' in elem.attrib` and `if 'VPOS' in elem.attrib` — never apply crop delta to WIDTH or HEIGHT.

### Pitfall 4: Multi-Page TIFF Handling
**What goes wrong:** Some archival TIFFs are multi-page. `Image.open()` opens only the first frame. Processing may succeed silently while ignoring remaining pages.
**Why it happens:** Pillow's `Image.open()` lazy-loads the first frame; `image.n_frames` reveals if more frames exist.
**How to avoid:** After `Image.open()`, check `getattr(img, 'n_frames', 1)`. If `> 1`: either error out with a clear message (`ERROR: multi-page TIFF not supported in Phase 1`) or process only frame 0 with a warning. CONTEXT.md designates this as Claude's discretion — recommend logging a warning and processing frame 0 only.

### Pitfall 5: lxml Namespace Isolation After Rewrite
**What goes wrong:** After string-replace rewrite, `xsi:schemaLocation` still points to the ALTO 3.x XSD URL. Some validators reject this as contradictory.
**Why it happens:** String replace only changes the namespace URI in element/attribute names, not in `xsi:schemaLocation` attribute value.
**How to avoid:** After rewrite, explicitly remove or update the `xsi:schemaLocation` attribute on the root element. Setting it to the ALTO 2.1 CCS schema URL or removing it entirely is both valid.

---

## Code Examples

Verified patterns from live testing:

### DPI Extraction from TIFF
```python
# Verified: Pillow 11.1.0 — image.info.get('dpi') returns None when no DPI tag
from PIL import Image
from pathlib import Path

def load_tiff(path: Path) -> tuple[Image.Image, tuple[float, float], list[str]]:
    """Returns (image, (dpi_x, dpi_y), warnings)."""
    warnings = []
    img = Image.open(path)
    dpi = img.info.get('dpi')
    if dpi is None:
        dpi = (300.0, 300.0)
        warnings.append('no DPI tag, using 300')
    return img, dpi, warnings
```

### Crop Detection (Corrected Threshold)
```python
# Source: verified live against simulated scan image — THRESH_BINARY is correct
import cv2
import numpy as np
from PIL import Image

def detect_crop_box(
    image: Image.Image,
    padding: int = 50,
    min_ratio: float = 0.40,
    max_ratio: float = 0.98,
) -> tuple[tuple[int,int,int,int], bool]:
    """Returns ((left, upper, right, lower), fallback_used)."""
    img_w, img_h = image.size
    orig_area = img_w * img_h
    img_array = np.array(image.convert('RGB'))
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    # THRESH_BINARY: light page content (high pixel value) → white
    # THRESH_OTSU: automatic threshold selection
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return (0, 0, img_w, img_h), True
    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
    ratio = (w * h) / orig_area
    if not (min_ratio <= ratio <= max_ratio):
        return (0, 0, img_w, img_h), True
    left = max(0, x - padding)
    upper = max(0, y - padding)
    right = min(img_w, x + w + padding)
    lower = min(img_h, y + h + padding)
    return (left, upper, right, lower), False
```

### Tesseract OCR Call
```python
# Source: verified against pytesseract 0.3.13 + tesseract 5.5.1
import pytesseract
from PIL import Image

def run_ocr(image: Image.Image, lang: str = 'deu', psm: int = 1, dpi: int = 300) -> bytes:
    """Returns raw ALTO XML bytes from Tesseract (ALTO 3.x namespace)."""
    config = f'--psm {psm} --dpi {dpi}'
    result = pytesseract.image_to_alto_xml(image, lang=lang, config=config)
    return result if isinstance(result, bytes) else result.encode('utf-8')
```

### Namespace Rewrite + Crop Offset
```python
# Source: verified against lxml 5.3.0 — string-replace is the correct lxml approach
from lxml import etree

ALTO3_NS = 'http://www.loc.gov/standards/alto/ns-v3#'
ALTO21_NS = 'http://schema.ccs-gmbh.com/ALTO'

POSITIONAL_TAGS = {
    'Page', 'PrintSpace', 'ComposedBlock', 'TextBlock',
    'TextLine', 'String', 'SP', 'Illustration', 'GraphicalElement',
}

def build_alto21(
    alto_bytes: bytes,
    crop_box: tuple[int, int, int, int],
) -> bytes:
    """Rewrites namespace to ALTO 2.1, applies crop offset, returns UTF-8 bytes."""
    # 1. Parse
    root = etree.fromstring(alto_bytes)

    # 2. Apply crop offset BEFORE namespace rewrite (so tag lookup uses ALTO3 ns)
    crop_x, crop_y = crop_box[0], crop_box[1]
    if crop_x != 0 or crop_y != 0:
        ns_prefix = '{' + ALTO3_NS + '}'
        for elem in root.iter():
            local = elem.tag[len(ns_prefix):] if elem.tag.startswith(ns_prefix) else elem.tag
            if local in POSITIONAL_TAGS:
                if 'HPOS' in elem.attrib:
                    elem.attrib['HPOS'] = str(int(elem.attrib['HPOS']) + crop_x)
                if 'VPOS' in elem.attrib:
                    elem.attrib['VPOS'] = str(int(elem.attrib['VPOS']) + crop_y)

    # 3. Rewrite namespace via string replace
    xml_str = etree.tostring(root, encoding='unicode')
    xml_str = xml_str.replace(ALTO3_NS, ALTO21_NS)
    # Remove xsi:schemaLocation pointing to ALTO 3 XSD
    xml_str = xml_str.replace(
        'xsi:schemaLocation="http://www.loc.gov/standards/alto/ns-v3# '
        'http://www.loc.gov/alto/v3/alto-3-0.xsd"',
        ''
    )

    # 4. Re-parse and serialize with XML declaration
    new_root = etree.fromstring(xml_str.encode())
    return etree.tostring(
        new_root,
        xml_declaration=True,
        encoding='UTF-8',
        pretty_print=True,
    )
```

### Word Count Extraction
```python
# Source: lxml element iteration (verified pattern)
def count_words(alto_root: etree._Element, namespace: str) -> int:
    """Count String elements in ALTO output."""
    ns_prefix = '{' + namespace + '}'
    return sum(
        1 for elem in alto_root.iter()
        if elem.tag == f'{ns_prefix}String' or elem.tag == 'String'
    )
```

### Error/Output Line
```python
import sys, time

def process_tiff(tiff_path: Path, output_dir: Path, lang: str,
                 psm: int, padding: int, no_crop: bool) -> None:
    warnings = []
    t0 = time.monotonic()
    try:
        img, dpi, load_warnings = load_tiff(tiff_path)
        warnings.extend(load_warnings)

        if no_crop:
            crop_box = (0, 0, img.size[0], img.size[1])
        else:
            crop_box, fallback = detect_crop_box(img, padding=padding)
            if fallback:
                warnings.append('crop fallback, using full image')

        cropped = img.crop(crop_box)
        alto_bytes = run_ocr(cropped, lang=lang, psm=psm, dpi=int(dpi[0]))
        alto_out = build_alto21(alto_bytes, crop_box)

        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / 'alto' / (tiff_path.stem + '.xml')
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(alto_out)

        root = etree.fromstring(alto_out)
        word_count = count_words(root, ALTO21_NS)
        elapsed = time.monotonic() - t0
        warn_str = (' [WARN: ' + '; '.join(warnings) + ']') if warnings else ''
        print(f"{tiff_path.name} → {out_path} ({elapsed:.1f}s, {word_count} words){warn_str}")

    except Exception as e:
        print(f"ERROR: {tiff_path.name}: {e}", file=sys.stderr)
        sys.exit(1)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Build ALTO from TSV manually | Use `image_to_alto_xml()` directly | pytesseract 0.3.5+ (2020) | Eliminates manual block/line/word nesting; ALTO structure comes from Tesseract |
| Fixed threshold for border detection | Otsu automatic threshold | OpenCV 2.x+ | Adapts to varying scan exposure; no manual tuning |
| `MeasurementUnit=mm10` with DPI conversion | `MeasurementUnit=pixel` | ALTO 2.1 XSD (both valid) | Eliminates floating-point DPI arithmetic; pixel coords directly usable |
| Threading for OCR parallelism | ProcessPoolExecutor | Python 3.2+ | Bypasses GIL for CPU-bound Tesseract processes (Phase 2 concern) |

**Deprecated/outdated:**
- Tesseract 4.x: LSTM quality was lower for German historical text; Tesseract 5.x is now standard
- `cv2.imread()` for primary TIFF I/O: No DPI preservation; use Pillow

---

## Open Questions

1. **Which ALTO 2.1 namespace does the target Goobi instance expect?**
   - What we know: Two valid namespaces exist — CCS-GmbH (`http://schema.ccs-gmbh.com/ALTO`) and LOC ns-v2 (`http://www.loc.gov/standards/alto/ns-v2#`). CONTEXT.md specifies CCS-GmbH.
   - What's unclear: Older Goobi installations (pre-2015) commonly used CCS-GmbH; newer ones may use ns-v2. Without access to the specific Goobi instance, this cannot be verified from research.
   - Recommendation: Implement CCS-GmbH as specified. Make the target namespace a single named constant (`ALTO21_NS`) so it can be changed with a one-line edit. Confirm with operator before Phase 1 is declared production-ready.

2. **Should MeasurementUnit stay `pixel` or be converted to `mm10`?**
   - What we know: Tesseract outputs `pixel`; ALTO 2.1 XSD allows both; `pixel` avoids DPI conversion complexity.
   - What's unclear: Some Goobi instances or DFG Viewer configurations expect `mm10` for proper highlight scaling.
   - Recommendation: Default to `pixel` in Phase 1. If Goobi displays word highlights at wrong positions, convert to mm10 using `coord_mm10 = pixel_coord * 10 / (dpi / 25.4)`.

3. **Multi-page TIFFs: process frame 0 or error?**
   - What we know: CONTEXT.md says "treat as single-page or error" at Claude's discretion.
   - Recommendation: Process frame 0 only with a warning appended to the output line: `[WARN: multi-page TIFF, processed frame 0 only]`. This is non-destructive and keeps the batch running.

4. **Threshold direction for specific scan set**
   - What we know: `THRESH_BINARY` is correct for typical archival scans (dark border, light page). Verified on simulated images.
   - What's unclear: Some scan batches may have inverted characteristics (white border, light background).
   - Recommendation: Test crop detection on 5-10 representative Zeitschriften TIFFs before marking PIPE-02 complete. If fallback triggers on most files, re-examine threshold direction.

---

## Sources

### Primary (HIGH confidence)
- Live environment: tesseract 5.5.1, pytesseract 0.3.13, lxml 5.3.0, Pillow 11.1.0, opencv-python 4.11.0 — all verified installed
- `http://www.loc.gov/standards/alto/alto.xsd` — ALTO 2.1 official XSD; MeasurementUnit enum values (`pixel`, `mm10`, `inch1200`) confirmed; `targetNamespace="http://www.loc.gov/standards/alto/ns-v2#"` confirmed
- Live Tesseract output: namespace `http://www.loc.gov/standards/alto/ns-v3#` confirmed; `MeasurementUnit=pixel` confirmed
- ARCHITECTURE.md, STACK.md, PITFALLS.md — project research documents (previously authored)

### Secondary (MEDIUM confidence)
- WebSearch: confirmed CCS-GmbH namespace is pre-LOC ALTO 2.0/1.x era; LOC adopted ALTO standard at 2.0 and used `ns-v2` — [ALTO schema history via altoxml/schema GitHub](https://github.com/altoxml/schema/blob/master/v2/alto-2-0.xsd)
- Live lxml test: namespace string-replace rewrite verified to produce correct root tag; crop offset verified to correctly increment HPOS/VPOS for test document

### Tertiary (LOW confidence)
- Goobi ALTO namespace preference: could not verify which namespace the specific target Goobi installation expects — no accessible Goobi source code search returned definitive results. Proceeding per CONTEXT.md specification (CCS-GmbH).

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified installed with exact versions
- Architecture: HIGH — core patterns verified via live code execution
- Pitfalls: HIGH for threshold direction and crop offset; MEDIUM for namespace (Goobi-specific)
- Namespace decision: MEDIUM — schema-valid but Goobi-instance-specific

**Research date:** 2026-02-24
**Valid until:** 2026-05-24 (90 days — stable libraries, tesseract version unlikely to change)

**Key correction from STACK.md:** STACK.md crop algorithm uses `THRESH_BINARY_INV` — this is WRONG for the intended scan type. Correct algorithm uses `THRESH_BINARY`. The planner must use the corrected algorithm from this document.
