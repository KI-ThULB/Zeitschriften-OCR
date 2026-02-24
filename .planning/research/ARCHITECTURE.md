# Architecture Research: TIFF Batch OCR → ALTO XML Pipeline

## Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                           │
│  parse args → validate paths → resolve file list → dispatch │
└────────────────────────┬────────────────────────────────────┘
                         │ list of TIFF paths
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               Batch Orchestrator                             │
│  ProcessPoolExecutor → dispatch → collect results → report  │
└────────────────────────┬────────────────────────────────────┘
                         │ single TIFF path (per worker)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Pipeline Worker                             │
│  (runs in subprocess — fully isolated)                       │
│                                                              │
│  1. ImageLoader     — open TIFF, extract DPI metadata        │
│  2. CropDetector    — detect content boundary, compute box   │
│  3. Cropper         — apply crop box to image                │
│  4. OCRRunner       — run Tesseract on cropped image         │
│  5. ALTOBuilder     — parse Tesseract output → ALTO 2.1 XML  │
│  6. ALTOWriter      — validate and write XML to output path  │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow: Single TIFF

```
TIFF file on disk
    │
    ▼ Pillow lazy open
PIL Image + DPI tuple (e.g., (400.0, 400.0))
    │
    ▼ convert to numpy array for OpenCV
numpy uint8 array (RGB)
    │
    ▼ grayscale → threshold → find contours → boundingRect
CropBox(x, y, w, h) — pixel coordinates in original image space
    │
    ▼ PIL Image.crop(box)
Cropped PIL Image (content area only, DPI preserved)
    │
    ▼ pytesseract.image_to_alto_xml(image, lang='deu', config='--psm 1')
ALTO XML string (Tesseract native output — may be ALTO 3.x namespace)
    │
    ▼ lxml parse → fix namespace → validate schema → serialize
ALTO 2.1 XML string (validated)
    │
    ▼ write to output/alto/<stem>.xml
Output file on disk
```

## Key Interfaces

### ImageLoader
```python
def load_tiff(path: Path) -> tuple[Image.Image, tuple[float, float]]:
    """Returns (image, (dpi_x, dpi_y)). Falls back to (300.0, 300.0) if no DPI tag."""
```

### CropDetector
```python
def detect_crop_box(image: Image.Image, padding: int = 50) -> tuple[int,int,int,int]:
    """Returns (left, upper, right, lower) in PIL crop convention.
    Falls back to original bounds if detection fails or result < 50% of original area."""
```

### OCRRunner
```python
def run_ocr(image: Image.Image, lang: str, psm: int) -> str:
    """Returns raw ALTO XML string from Tesseract."""
```

### ALTOBuilder
```python
def fix_alto_namespace(alto_xml: str, dpi: tuple[float,float]) -> bytes:
    """Corrects namespace to ALTO 2.1, injects DPI into MeasurementUnit,
    returns validated UTF-8 bytes ready to write."""
```

## Parallel Processing Model

**ProcessPoolExecutor** — not ThreadPoolExecutor.

Reason: Tesseract OCR is CPU-bound. Python's GIL prevents true parallelism with threads for CPU-bound work. Each process gets its own interpreter and its own Tesseract subprocess. Memory isolation means one worker's crash (e.g., malformed TIFF) does not affect others.

```python
# Each worker is fully independent
with ProcessPoolExecutor(max_workers=args.workers) as pool:
    futures = {pool.submit(process_single_tiff, path, args): path
               for path in pending_files}
    for future in as_completed(futures):
        path = futures[future]
        try:
            result = future.result()
        except Exception as e:
            log_error(path, e)
```

**Worker count guidance:**
- Default: `min(os.cpu_count(), 4)` — conservative default (large TIFFs are memory-intensive)
- Each worker may hold 1-2 large TIFFs in memory during processing
- A 240 MB TIFF uncompressed RGB at 400 DPI ≈ 500-800 MB RAM per worker
- Recommend: on a 16 GB machine, max 4 workers with 240 MB TIFFs

## Output Directory Structure

```
<output_dir>/
└── alto/
    ├── scan_001.xml
    ├── scan_002.xml
    └── ...
```

- Input: `/path/to/scans/scan_001.tif`
- Output: `<output_dir>/alto/scan_001.xml`
- Stem mapping: `Path(tiff_path).stem + '.xml'`

## Skip Logic

```python
output_path = output_dir / 'alto' / (Path(tiff_path).stem + '.xml')
if output_path.exists() and not args.force:
    return SkipResult(path=tiff_path, reason='already_exists')
```

## ALTO 2.1 Coordinate System

ALTO 2.1 uses `HPOS`, `VPOS`, `WIDTH`, `HEIGHT` measured in 1/10 mm (tenths of millimeters) by default when `MeasurementUnit` is `mm10`.

Tesseract outputs pixel coordinates. Conversion:
```
hpos_mm10 = pixel_x * 10 / (dpi / 25.4)
vpos_mm10 = pixel_y * 10 / (dpi / 25.4)
```

**Critical:** The DPI value used for this conversion must be the DPI of the **cropped image** (same as original, since cropping doesn't change DPI). If DPI is missing from TIFF metadata, default to 300.

## Build Order (Phase Dependencies)

```
Phase 1: Core pipeline (ImageLoader + CropDetector + OCRRunner + ALTOBuilder + ALTOWriter)
         → Must be working end-to-end before parallelism is useful
         → Test with 3-5 files before scaling

Phase 2: Batch orchestration (CLI + ProcessPoolExecutor + skip logic + error logging)
         → Depends on Phase 1 working correctly for a single file

Phase 3: Robustness (error handling, validation, reporting, edge cases)
         → Depends on Phase 2 for realistic error scenarios
```
