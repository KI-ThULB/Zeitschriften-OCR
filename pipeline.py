#!/usr/bin/env python3
"""pipeline.py — Single-TIFF to ALTO 2.1 OCR pipeline.

Usage:
    python pipeline.py --input <tiff_path> --output <output_dir>
"""
import argparse
import sys
import time
from pathlib import Path

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

    CRITICAL: crop offset is applied BEFORE namespace rewrite. The offset uses ALTO3_NS
    to find elements; after the string replace the namespace changes to ALTO21_NS and
    the tag lookup would fail.

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

    # Step 2: Apply crop offset BEFORE namespace rewrite (uses ALTO3_NS for element lookup)
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

    # Step 3: Serialize to string for namespace rewrite
    xml_str = etree.tostring(root, encoding='unicode')

    # Step 4: Rewrite namespace from ALTO 3.x to ALTO 2.1 (CCS-GmbH)
    xml_str = xml_str.replace(ALTO3_NS, ALTO21_NS)

    # Step 5: Remove the ALTO 3 xsi:schemaLocation to avoid contradictory schema reference
    xml_str = xml_str.replace(
        'xsi:schemaLocation="http://www.loc.gov/standards/alto/ns-v3# '
        'http://www.loc.gov/alto/v3/alto-3-0.xsd"',
        ''
    )

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
# CLI entry point (argparse skeleton — main logic in Plan 02)
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

    # Stub: process_tiff() implemented in Plan 02
    pass


if __name__ == '__main__':
    main()
