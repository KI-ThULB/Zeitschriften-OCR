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

# run_ocr, build_alto21, count_words, process_tiff — implemented in 01-02-PLAN


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
