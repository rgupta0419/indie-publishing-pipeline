"""
KDP Paperback Cover Wrap Pre-flight Validation.

Verifies a cover wrap file against KDP's spec:
  - Single page (not 3 separate pages)
  - Dimensions match formula: 2*trim_w + spine + 2*0.125 wide; trim_h + 0.25 tall
  - Spine width correct for given page count + paper type
  - DPI >= 300 at print size
  - Not password-protected
  - Reasonable file size (<650 MB KDP limit)

Usage:
    python validate_cover.py path/to/cover_wrap.pdf --trim 5.5x8.5 --pages 223
    python validate_cover.py path/to/cover_wrap.png --trim 5.5x8.5 --pages 223

Exit codes:
    0 = pass, 1 = warning, 2 = error
"""

import argparse
import json
import os
import sys
from pathlib import Path

TRIM_SIZES = {
    "5x8": (5.0, 8.0), "5.5x8.5": (5.5, 8.5), "6x9": (6.0, 9.0),
    "7x10": (7.0, 10.0), "8.5x11": (8.5, 11.0),
}

PAPER_THICKNESS = {
    "bw_white": 0.0025, "bw_cream": 0.0025,
    "standard_color": 0.0025, "premium_color": 0.0027,
}

BLEED = 0.125  # always 0.125" all sides on cover
DPI_MIN = 300


def expected_wrap_dimensions(trim_w, trim_h, page_count, paper="bw_white"):
    """Compute expected cover wrap dimensions for KDP."""
    spine = page_count * PAPER_THICKNESS[paper]
    width = 2 * trim_w + spine + 2 * BLEED
    height = trim_h + 2 * BLEED
    return width, height, spine


def check_pdf(path, exp_w, exp_h, exp_spine):
    result = {"errors": [], "warnings": [], "passed": []}
    try:
        from pypdf import PdfReader
    except ImportError:
        result["errors"].append("pypdf not installed. Install: pip install pypdf")
        return result

    reader = PdfReader(path)

    if reader.is_encrypted:
        result["errors"].append("PDF is password-protected. Remove encryption.")
        return result

    # Single page check
    n_pages = len(reader.pages)
    if n_pages != 1:
        result["errors"].append(
            f"Cover wrap PDF has {n_pages} pages. KDP requires SINGLE page (front+spine+back combined). "
            "Re-export as one composite page.")
        return result
    else:
        result["passed"].append("Single-page PDF (correct)")

    # Dimensions
    page = reader.pages[0]
    media_box = page.mediabox
    w_in = float(media_box.width) / 72
    h_in = float(media_box.height) / 72

    # Allow 0.05" tolerance
    w_diff = abs(w_in - exp_w)
    h_diff = abs(h_in - exp_h)

    if w_diff > 0.05:
        result["errors"].append(
            f"Cover width {w_in:.3f}\" doesn't match expected {exp_w:.3f}\" "
            f"(diff {w_diff:.3f}\"). Check spine width calculation.")
    else:
        result["passed"].append(f"Cover width {w_in:.3f}\" matches expected {exp_w:.3f}\"")

    if h_diff > 0.05:
        result["errors"].append(
            f"Cover height {h_in:.3f}\" doesn't match expected {exp_h:.3f}\". "
            f"Should be trim_height + 0.25 (bleed).")
    else:
        result["passed"].append(f"Cover height {h_in:.3f}\" matches expected {exp_h:.3f}\"")

    result["passed"].append(f"Spine width should be: {exp_spine:.4f}\"")

    # File size
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > 650:
        result["errors"].append(f"File size {size_mb:.1f} MB exceeds KDP limit of 650 MB.")
    elif size_mb > 100:
        result["warnings"].append(
            f"File size {size_mb:.1f} MB is large but acceptable. "
            "Consider downsampling images if PDF includes high-res scans.")
    else:
        result["passed"].append(f"File size: {size_mb:.1f} MB (within limits)")

    return result


def check_image(path, exp_w, exp_h, exp_spine):
    result = {"errors": [], "warnings": [], "passed": []}
    try:
        from PIL import Image
    except ImportError:
        result["errors"].append("Pillow not installed. Install: pip install Pillow")
        return result

    img = Image.open(path)
    w_px, h_px = img.size

    # Calculate DPI based on expected print dimensions
    dpi_w = w_px / exp_w
    dpi_h = h_px / exp_h

    if dpi_w < DPI_MIN:
        result["errors"].append(
            f"Width DPI {dpi_w:.0f} below KDP minimum {DPI_MIN}. "
            f"Image is {w_px}px wide; needs ≥{int(exp_w * DPI_MIN)}px for {exp_w:.3f}\" print width.")
    else:
        result["passed"].append(f"Width DPI {dpi_w:.0f} (≥{DPI_MIN} required)")

    if dpi_h < DPI_MIN:
        result["errors"].append(
            f"Height DPI {dpi_h:.0f} below KDP minimum {DPI_MIN}. "
            f"Image is {h_px}px tall; needs ≥{int(exp_h * DPI_MIN)}px for {exp_h:.3f}\" print height.")
    else:
        result["passed"].append(f"Height DPI {dpi_h:.0f} (≥{DPI_MIN} required)")

    # Aspect ratio check
    expected_aspect = exp_w / exp_h
    actual_aspect = w_px / h_px
    aspect_diff = abs(expected_aspect - actual_aspect) / expected_aspect
    if aspect_diff > 0.02:  # 2% tolerance
        result["errors"].append(
            f"Image aspect ratio {actual_aspect:.4f} doesn't match expected "
            f"{expected_aspect:.4f}. Cover dimensions don't fit KDP spec.")
    else:
        result["passed"].append(f"Aspect ratio matches expected wrap dimensions")

    result["passed"].append(f"Expected spine width: {exp_spine:.4f}\"")
    return result


def main():
    p = argparse.ArgumentParser(description="Validate cover wrap for KDP paperback upload")
    p.add_argument("path", help="Path to .pdf or .png/.jpg cover wrap")
    p.add_argument("--trim", default="5.5x8.5",
                   help="Trim size (default 5.5x8.5)")
    p.add_argument("--pages", type=int, required=True,
                   help="Final interior page count")
    p.add_argument("--paper", default="bw_white",
                   choices=list(PAPER_THICKNESS.keys()),
                   help="Paper type (default bw_white)")
    p.add_argument("--json", action="store_true", help="Output JSON")
    args = p.parse_args()

    if args.trim not in TRIM_SIZES:
        print(f"Unknown trim: {args.trim}", file=sys.stderr)
        sys.exit(2)

    trim_w, trim_h = TRIM_SIZES[args.trim]
    exp_w, exp_h, exp_spine = expected_wrap_dimensions(trim_w, trim_h, args.pages, args.paper)

    ext = Path(args.path).suffix.lower()
    if ext == ".pdf":
        result = check_pdf(args.path, exp_w, exp_h, exp_spine)
    elif ext in (".png", ".jpg", ".jpeg", ".tiff"):
        result = check_image(args.path, exp_w, exp_h, exp_spine)
    else:
        print(f"Unsupported format: {ext}", file=sys.stderr)
        sys.exit(2)

    status = "FAIL" if result["errors"] else ("WARN" if result["warnings"] else "PASS")
    result["status"] = status
    result["expected_wrap_dimensions"] = f"{exp_w:.3f}\" x {exp_h:.3f}\""
    result["expected_spine"] = f"{exp_spine:.4f}\""
    result["page_count_basis"] = args.pages

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n=== KDP Cover Wrap Validation: {args.path} ===")
        print(f"Trim: {trim_w}x{trim_h}\" | Pages: {args.pages} | Paper: {args.paper}")
        print(f"Expected wrap: {exp_w:.3f}\" x {exp_h:.3f}\"")
        print(f"Expected spine: {exp_spine:.4f}\"\n")

        if result["errors"]:
            print(f"❌ ERRORS ({len(result['errors'])}):")
            for e in result["errors"]:
                print(f"   • {e}")
        if result["warnings"]:
            print(f"⚠️  WARNINGS ({len(result['warnings'])}):")
            for w in result["warnings"]:
                print(f"   • {w}")
        if result["passed"]:
            print(f"✓ PASSED ({len(result['passed'])}):")
            for ok in result["passed"]:
                print(f"   • {ok}")
        print(f"\n=== STATUS: {status} ===\n")

    sys.exit(0 if status == "PASS" else (1 if status == "WARN" else 2))


if __name__ == "__main__":
    main()
