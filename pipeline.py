#!/usr/bin/env python3
"""pipeline.py — Single-TIFF to ALTO 2.1 OCR pipeline.

Usage:
    python pipeline.py --input <tiff_path> --output <output_dir>
"""
import argparse
import json
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

import cv2
import numpy as np
from lxml import etree
from PIL import Image

import pytesseract

# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------

ALTO3_NS = 'http://www.loc.gov/standards/alto/ns-v3#'
ALTO21_NS = 'http://schema.ccs-gmbh.com/ALTO'  # CCS-GmbH namespace per user decision

POSITIONAL_TAGS = {
    'Page', 'PrintSpace', 'ComposedBlock', 'TextBlock',
    'TextLine', 'String', 'SP', 'Illustration', 'GraphicalElement',
}

# ---------------------------------------------------------------------------
# Foundation functions
# ---------------------------------------------------------------------------

def load_tiff(path: Path) -> tuple[Image.Image, tuple[float, float], list[str]]:
    """Load a TIFF file and extract DPI metadata.

    Returns:
        img: PIL Image (lazy-loaded, frame 0 for multi-page TIFFs)
        dpi: (x_dpi, y_dpi) as floats; (300.0, 300.0) if tag absent
        warnings: list of warning strings (empty for a clean file)
    """
    warnings: list[str] = []

    img = Image.open(path)

    # Multi-page TIFF handling — proceed with frame 0, log warning
    if getattr(img, 'n_frames', 1) > 1:
        warnings.append('multi-page TIFF, processed frame 0 only')

    # DPI extraction from TIFF metadata tag
    raw_dpi = img.info.get('dpi')
    if raw_dpi is None:
        dpi: tuple[float, float] = (300.0, 300.0)
        warnings.append('no DPI tag, using 300')
    else:
        dpi = (float(raw_dpi[0]), float(raw_dpi[1]))

    return img, dpi, warnings


def detect_crop_box(
    image: Image.Image,
    padding: int = 50,
    min_ratio: float = 0.40,
    max_ratio: float = 0.98,
) -> tuple[tuple[int, int, int, int], bool]:
    """Detect the printed page area within a scanned TIFF using OpenCV contour detection.

    For archival scans (dark scanner bed, light page content), THRESH_BINARY makes the
    light page content white so it becomes the largest contour.
    The inverse variant is intentionally NOT used here.

    Args:
        image: PIL Image of the scan
        padding: Pixels of margin to add around the detected area (default: 50)
        min_ratio: Minimum acceptable area ratio vs full image (default: 0.40)
        max_ratio: Maximum acceptable area ratio vs full image (default: 0.98)

    Returns:
        box: (left, upper, right, lower) crop box in pixel coordinates
        fallback_used: True if detection failed or ratio was out of bounds
    """
    img_w, img_h = image.size
    orig_area = img_w * img_h

    # Convert to numpy array via RGB to ensure consistent channel order
    img_array = np.array(image.convert('RGB'))

    # Convert to grayscale for thresholding
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

    # Otsu threshold: THRESH_BINARY (not INV) — light page content becomes white
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Find external contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return (0, 0, img_w, img_h), True

    # Get bounding rectangle of the largest contour (the page content)
    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))

    # Check if detected area ratio is within acceptable range
    ratio = (w * h) / orig_area
    if not (min_ratio <= ratio <= max_ratio):
        return (0, 0, img_w, img_h), True

    # Apply padding with bounds clamping
    left = max(0, x - padding)
    upper = max(0, y - padding)
    right = min(img_w, x + w + padding)
    lower = min(img_h, y + h + padding)

    return (left, upper, right, lower), False


# ---------------------------------------------------------------------------
# OCR and ALTO XML functions
# ---------------------------------------------------------------------------

def run_ocr(image: Image.Image, lang: str = 'deu', psm: int = 1, dpi: int = 300) -> bytes:
    """Run Tesseract OCR on a PIL Image and return raw ALTO XML bytes.

    Args:
        image: PIL Image to process (passed directly — pytesseract handles temp PNG internally)
        lang: Tesseract language code (default: 'deu')
        psm: Page segmentation mode (default: 1 — auto with OSD)
        dpi: DPI to pass to Tesseract via --dpi config flag

    Returns:
        ALTO XML as bytes (UTF-8)
    """
    config = f'--psm {psm} --dpi {dpi}'
    result = pytesseract.image_to_alto_xml(image, lang=lang, config=config)
    return result if isinstance(result, bytes) else result.encode('utf-8')


def build_alto21(alto_bytes: bytes, crop_box: tuple[int, int, int, int]) -> bytes:
    """Convert Tesseract ALTO 3.x XML to ALTO 2.1 (CCS-GmbH namespace) with crop offset applied.

    CRITICAL step order:
      Step 1: Parse raw Tesseract output.
      Step 2: Remove xsi:schemaLocation BEFORE serialization (while element is still parsed).
      Step 3: Apply crop offset BEFORE namespace rewrite (uses ALTO3_NS for element lookup).
      Step 4: Serialize to string for namespace rewrite.
      Step 5: Rewrite namespace from ALTO 3.x to ALTO 2.1 (CCS-GmbH).
      Step 6: Re-parse and serialize with XML declaration.

    The crop offset (Step 3) must run before the namespace string-replace (Step 5) because the
    offset uses ALTO3_NS tag names; after the string replace the namespace changes to ALTO21_NS
    and the tag lookup would fail.

    Args:
        alto_bytes: Raw ALTO XML bytes from Tesseract (uses ALTO 3.x namespace)
        crop_box: (left, upper, right, lower) crop box — HPOS offset by crop_box[0],
                  VPOS offset by crop_box[1]. WIDTH and HEIGHT are NOT modified.

    Returns:
        ALTO 2.1 XML bytes with UTF-8 XML declaration and pretty-printed
    """
    crop_x, crop_y = crop_box[0], crop_box[1]

    # Step 1: Parse the raw Tesseract output
    root = etree.fromstring(alto_bytes)

    # Step 2: Remove xsi:schemaLocation BEFORE serialization to avoid contradictory ALTO 3 XSD reference.
    # Must run before the namespace rewrite (Step 5), while the element is still parsed.
    root.attrib.pop('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', None)

    # Step 3: Apply crop offset BEFORE namespace rewrite (uses ALTO3_NS for element lookup)
    if crop_x != 0 or crop_y != 0:
        ns_prefix = '{' + ALTO3_NS + '}'
        for elem in root.iter():
            local = elem.tag[len(ns_prefix):] if elem.tag.startswith(ns_prefix) else elem.tag
            if local in POSITIONAL_TAGS:
                if 'HPOS' in elem.attrib:
                    elem.attrib['HPOS'] = str(int(elem.attrib['HPOS']) + crop_x)
                if 'VPOS' in elem.attrib:
                    elem.attrib['VPOS'] = str(int(elem.attrib['VPOS']) + crop_y)
                # WIDTH and HEIGHT are intentionally NOT modified — only HPOS and VPOS get the offset

    # Step 4: Serialize to string for namespace rewrite
    xml_str = etree.tostring(root, encoding='unicode')

    # Step 5: Rewrite namespace from ALTO 3.x to ALTO 2.1 (CCS-GmbH)
    xml_str = xml_str.replace(ALTO3_NS, ALTO21_NS)

    # Step 6: Re-parse and serialize with XML declaration
    new_root = etree.fromstring(xml_str.encode())
    return etree.tostring(new_root, xml_declaration=True, encoding='UTF-8', pretty_print=True)


def count_words(alto_root: etree._Element, namespace: str) -> int:
    """Count all String elements in an ALTO XML tree.

    Args:
        alto_root: Root element of the parsed ALTO XML
        namespace: XML namespace string (e.g. 'http://schema.ccs-gmbh.com/ALTO')

    Returns:
        Total number of String elements (each represents one OCR word)
    """
    count = 0
    for elem in alto_root.iter():
        if elem.tag == f'{{{namespace}}}String' or elem.tag == 'String':
            count += 1
    return count


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def process_tiff(
    tiff_path: Path,
    output_dir: Path,
    lang: str,
    psm: int,
    padding: int,
    no_crop: bool,
) -> None:
    """Process a single TIFF file through the full OCR pipeline.

    Loads the TIFF, optionally detects the crop box, runs OCR, converts to
    ALTO 2.1 XML, writes output, and prints a single result line to stdout.

    Args:
        tiff_path: Path to the input TIFF file
        output_dir: Root output directory; ALTO XML is written to output_dir/alto/{stem}.xml
        lang: Tesseract language code (e.g. 'deu')
        psm: Tesseract page segmentation mode
        padding: Padding pixels for crop box detection
        no_crop: If True, bypass border detection and use full image bounds
    """
    warnings_list: list[str] = []
    t0 = time.monotonic()

    try:
        # Load TIFF
        img, dpi, load_warnings = load_tiff(tiff_path)
        warnings_list.extend(load_warnings)

        # Determine crop box
        if no_crop:
            crop_box = (0, 0, img.size[0], img.size[1])
        else:
            crop_box, fallback = detect_crop_box(img, padding=padding)
            if fallback:
                warnings_list.append('crop fallback, using full image')

        # Crop and OCR
        cropped = img.crop(crop_box)
        alto_bytes = run_ocr(cropped, lang=lang, psm=psm, dpi=int(dpi[0]))

        # Build ALTO 2.1 XML with crop offset applied
        alto_out = build_alto21(alto_bytes, crop_box)

        # Write output
        out_path = output_dir / 'alto' / (tiff_path.stem + '.xml')
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(alto_out)

        # Word count
        root = etree.fromstring(alto_out)
        word_count = count_words(root, ALTO21_NS)

        # Elapsed time
        elapsed = time.monotonic() - t0

        # Warnings suffix
        warn_str = (' [WARN: ' + '; '.join(warnings_list) + ']') if warnings_list else ''

        print(f"{tiff_path.name} \u2192 {out_path} ({elapsed:.1f}s, {word_count} words){warn_str}")

    except Exception as e:
        print(f"ERROR: {tiff_path.name}: {e}", file=sys.stderr)
        raise


# ---------------------------------------------------------------------------
# Batch helpers
# ---------------------------------------------------------------------------

def validate_tesseract(lang: str) -> None:
    """Validate Tesseract is installed and the requested language pack is available.

    Call this BEFORE creating ProcessPoolExecutor — validation failure exits cleanly
    with no dangling worker processes.

    Raises SystemExit(1) with a clear error message if either check fails.
    """
    try:
        available = pytesseract.get_languages()
    except pytesseract.TesseractNotFoundError:
        print(
            "ERROR: Tesseract OCR is not installed or not on PATH.\n"
            "  macOS:  brew install tesseract\n"
            "  Ubuntu: apt install tesseract-ocr",
            file=sys.stderr,
        )
        sys.exit(1)

    if lang not in available:
        print(
            f"ERROR: Tesseract language pack '{lang}' is not installed.\n"
            f"  Available packs: {', '.join(sorted(available))}\n"
            f"  macOS:  brew install tesseract-lang\n"
            f"  Ubuntu: apt install tesseract-ocr-{lang}",
            file=sys.stderr,
        )
        sys.exit(1)


def discover_tiffs(input_dir: Path) -> list[Path]:
    """Find all .tif/.tiff files in input_dir (case-insensitive suffix), sorted for deterministic ordering."""
    return sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in ('.tif', '.tiff')
    )


def write_error_log(output_dir: Path, errors: list[dict]) -> 'Path | None':
    """Write per-file error entries to a JSONL file in output_dir.

    Each entry has keys: file, exc_type, exc_message, traceback.
    File is named errors_{timestamp}.jsonl (1-second granularity is sufficient).
    Returns the log path, or None if errors is empty.
    """
    if not errors:
        return None
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = output_dir / f'errors_{timestamp}.jsonl'
    with log_path.open('w', encoding='utf-8') as f:
        for entry in errors:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    return log_path


def run_batch(
    tiff_files: list,
    output_dir: Path,
    workers: int,
    lang: str,
    psm: int,
    padding: int,
    force: bool,
) -> tuple:
    """Run OCR on all tiff_files in parallel using ProcessPoolExecutor.

    Implements:
      BATC-01: Parallel processing with configurable worker count
      BATC-02: Skip-if-exists logic (bypassed by force=True)
      BATC-03: Per-file error isolation — one failure does not abort the batch
      BATC-04: Error collection returned as list of dicts for write_error_log()

    Returns:
        (processed_count, skipped_count, error_list)
        error_list entries: {file, exc_type, exc_message, traceback}
    """
    errors = []
    skipped = 0
    processed = 0

    # BATC-02: Separate skip check from submission
    to_process = []
    for tiff_path in tiff_files:
        out_path = output_dir / 'alto' / (tiff_path.stem + '.xml')
        if not force and out_path.exists():
            skipped += 1
        else:
            to_process.append(tiff_path)

    if skipped:
        print(f"Skipping {skipped} already-processed file(s). Use --force to reprocess.")

    if not to_process:
        return processed, skipped, errors

    # BATC-01: ProcessPoolExecutor — process-based parallelism bypasses GIL
    # BATC-03: submit() + as_completed() isolates per-file failures
    # NOTE: process_tiff() must NOT call sys.exit() (fixed in Plan 01) — it must raise
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_tiff, tiff_path, output_dir, lang, psm, padding, False): tiff_path
            for tiff_path in to_process
        }
        # tqdm wraps the as_completed iterator; total= is required (as_completed has no __len__)
        with tqdm(total=len(futures), unit='file', desc='OCR') as pbar:
            for fut in as_completed(futures):
                tiff_path = futures[fut]
                try:
                    fut.result()
                    processed += 1
                except Exception as e:
                    # BATC-04: Collect per-file error with full traceback
                    # traceback.format_exc() captures the _RemoteTraceback chain from the worker
                    errors.append({
                        'file': str(tiff_path),
                        'exc_type': type(e).__name__,
                        'exc_message': str(e),
                        'traceback': traceback.format_exc(),
                    })
                finally:
                    pbar.update(1)

    return processed, skipped, errors


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description='Process a single TIFF to ALTO 2.1 XML')
    parser.add_argument('--input', required=True, type=Path, help='Path to input TIFF file')
    parser.add_argument('--output', required=True, type=Path, help='Output directory')
    parser.add_argument('--lang', default='deu', help='Tesseract language (default: deu)')
    parser.add_argument('--psm', type=int, default=1, help='Tesseract page segmentation mode (default: 1)')
    parser.add_argument('--padding', type=int, default=50, help='Crop padding in pixels (default: 50)')
    parser.add_argument('--no-crop', action='store_true', dest='no_crop',
                        help='Bypass border detection, use full image bounds')
    args = parser.parse_args()

    tiff_path = args.input
    if not tiff_path.exists():
        print(f"ERROR: Input file not found: {tiff_path}", file=sys.stderr)
        sys.exit(1)

    process_tiff(
        tiff_path=tiff_path,
        output_dir=args.output,
        lang=args.lang,
        psm=args.psm,
        padding=args.padding,
        no_crop=args.no_crop,
    )


if __name__ == '__main__':
    main()
