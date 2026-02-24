# Stack Research: TIFF Batch OCR → ALTO XML Pipeline

## Recommended Stack

### Image I/O — Large TIFF Files

**Primary: Pillow (PIL) >= 10.x**
- `pip install Pillow`
- Handles multi-page TIFFs, preserves DPI metadata from EXIF/TIFF tags
- Use `Image.open()` with lazy loading — does NOT load the full file into RAM until pixels are accessed
- Extract DPI via `image.info.get('dpi')` — critical for ALTO coordinate correctness
- Confidence: HIGH

**Alternative for very large TIFFs: tifffile >= 2024.x**
- `pip install tifffile`
- Better for BigTIFF and scientific scans, direct numpy array output
- More complex API; Pillow sufficient for archival JPEGcompressed or uncompressed TIFFs
- Confidence: MEDIUM

**Do NOT use: OpenCV `cv2.imread()` for primary I/O**
- OpenCV loads the full image into RAM immediately
- No DPI metadata preservation
- Use only for the crop detection step (convert from Pillow array)

### Border/Margin Detection and Cropping — OpenCV

**Primary: opencv-python >= 4.9.x**
- `pip install opencv-python-headless` (no GUI dependencies — correct for server/batch use)
- Standard approach: convert to grayscale → threshold → find contours → bounding rect
- `cv2.findContours()` with `cv2.RETR_EXTERNAL` finds outer content boundary
- `cv2.boundingRect()` gives crop box
- Confidence: HIGH

**Crop detection algorithm (proven pattern):**
```python
gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
_, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
```
- Add configurable padding margin (e.g., 50px) around detected bounding box
- Fallback: if detection fails or crop box < 50% of original, use original image

### Tesseract Python Bindings

**Primary: pytesseract >= 0.3.13**
- `pip install pytesseract`
- Wraps Tesseract CLI; requires Tesseract binary installed separately
- `pytesseract.image_to_alto_xml(image, lang='deu')` — direct ALTO XML output
- Tesseract 5.x (LSTM engine) — significantly better than 4.x for German
- Install Tesseract: `brew install tesseract tesseract-lang` (macOS), `apt install tesseract-ocr tesseract-ocr-deu` (Linux)
- Confidence: HIGH

**Tesseract version: 5.3.x+**
- LSTM engine (default `--oem 1`) — use for modern German text
- Language: `deu` (standard German)
- Page segmentation: `--psm 1` (auto page seg with OSD) or `--psm 3` (auto without OSD)

**Do NOT use: tesserocr**
- Requires Tesseract compiled as library; complex install; no advantage for ALTO output

### ALTO 2.1 XML Generation

**Primary: pytesseract ALTO output + lxml for post-processing**
- `pip install lxml`
- `pytesseract.image_to_alto_xml()` returns ALTO 3.x by default — requires namespace correction to ALTO 2.1
- ALTO 2.1 namespace: `xmlns="http://schema.ccs-gmbh.com/ALTO"`
- Post-process with lxml to fix namespace, strip unknown elements, validate schema
- Confidence: HIGH

**ALTO 2.1 schema validation:**
- Schema available at: http://www.loc.gov/standards/alto/alto.xsd (v2.1)
- Use `lxml.etree.XMLSchema` for validation during development

**Alternative: Build ALTO XML from tesseract TSV output**
- `pytesseract.image_to_data()` returns word-level data with coordinates
- Build ALTO manually with lxml ElementTree — full control over structure
- More work but guaranteed ALTO 2.1 conformance
- Recommended if pytesseract ALTO output has namespace issues

### Parallel Batch Processing

**Primary: concurrent.futures.ProcessPoolExecutor**
- Standard library — no extra dependencies
- Process-based (not threads) — bypasses Python GIL for CPU-bound OCR
- Each worker gets its own Tesseract process
- `max_workers = os.cpu_count()` or configurable via CLI
- Confidence: HIGH

**Pattern:**
```python
with ProcessPoolExecutor(max_workers=workers) as executor:
    futures = {executor.submit(process_tiff, f): f for f in tiff_files}
    for future in as_completed(futures):
        result = future.result()
```

**Do NOT use: multiprocessing.Pool with `map()`**
- No individual error isolation — one failure can affect pool state
- ProcessPoolExecutor with individual futures is safer

### Progress Reporting

**Primary: tqdm >= 4.66.x**
- `pip install tqdm`
- Thread-safe progress bar compatible with concurrent.futures
- Confidence: HIGH

### CLI Interface

**Primary: argparse (stdlib)**
- No extra dependencies
- Sufficient for: `--input`, `--output`, `--workers`, `--lang`, `--padding`, `--force`
- Confidence: HIGH

## Full Requirements Summary

```
Pillow>=10.0.0
opencv-python-headless>=4.9.0
pytesseract>=0.3.13
lxml>=5.0.0
tqdm>=4.66.0
```

System deps: `tesseract-ocr`, `tesseract-ocr-deu` (Linux) / `tesseract tesseract-lang` (macOS via brew)

## What NOT to Use

| Library | Reason to Avoid |
|---------|----------------|
| `pdf2image` | For PDFs, not TIFFs |
| `wand` (ImageMagick) | Heavy dependency, slower than Pillow for this use case |
| `celery` / `redis` | Overkill for a local batch tool |
| `asyncio` | Wrong model for CPU-bound OCR; use ProcessPool |
| `tesserocr` | Complex native install, no ALTO advantage |
