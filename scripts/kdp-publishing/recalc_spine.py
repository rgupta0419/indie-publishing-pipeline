"""
Calculate KDP cover spine width from page count.

Usage:
    python recalc_spine.py 223                  # default B&W white paper
    python recalc_spine.py 300 --paper bw_cream
    python recalc_spine.py 223 --paper standard_color

Outputs:
    spine_width_in: calculated spine width
    expected_wrap: full cover wrap dimensions for the spine
    kdp_buffered: KDP-recommended spine with +0.005" buffer
"""

import argparse
import json
import sys

PAPER_THICKNESS = {
    "bw_white": 0.0025, "bw_cream": 0.0025,
    "standard_color": 0.0025, "premium_color": 0.0027,
}

TRIM_SIZES = {
    "5x8": (5.0, 8.0), "5.5x8.5": (5.5, 8.5), "6x9": (6.0, 9.0),
    "7x10": (7.0, 10.0), "8.5x11": (8.5, 11.0),
}

BLEED = 0.125


def main():
    p = argparse.ArgumentParser(description="Calculate KDP spine width from page count")
    p.add_argument("pages", type=int, help="Interior page count")
    p.add_argument("--paper", default="bw_white", choices=list(PAPER_THICKNESS.keys()))
    p.add_argument("--trim", default="5.5x8.5", choices=list(TRIM_SIZES.keys()))
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    thickness = PAPER_THICKNESS[args.paper]
    spine = args.pages * thickness
    spine_buffered = spine + 0.005

    trim_w, trim_h = TRIM_SIZES[args.trim]
    wrap_w = 2 * trim_w + spine + 2 * BLEED
    wrap_h = trim_h + 2 * BLEED
    wrap_w_buffered = 2 * trim_w + spine_buffered + 2 * BLEED

    output = {
        "page_count": args.pages,
        "paper_type": args.paper,
        "thickness_per_page": thickness,
        "trim_size": args.trim,
        "spine_width_in": round(spine, 4),
        "spine_with_kdp_buffer": round(spine_buffered, 4),
        "cover_wrap_width_in": round(wrap_w, 4),
        "cover_wrap_height_in": round(wrap_h, 4),
        "cover_wrap_with_buffer_width_in": round(wrap_w_buffered, 4),
        "pixel_dimensions_at_300_dpi": {
            "wrap_width_px": round(wrap_w * 300),
            "wrap_height_px": round(wrap_h * 300),
            "spine_width_px": round(spine * 300),
        },
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"\n=== Spine Width Calculation ===")
        print(f"Page count: {args.pages}")
        print(f"Paper: {args.paper} (thickness {thickness}\"/page)")
        print(f"Trim: {args.trim}")
        print(f"")
        print(f"Spine width: {spine:.4f}\"")
        print(f"With KDP buffer (+0.005): {spine_buffered:.4f}\"")
        print(f"")
        print(f"Cover wrap dimensions:")
        print(f"  Width:  {wrap_w:.4f}\" ({round(wrap_w * 300)} px @ 300 DPI)")
        print(f"  Height: {wrap_h:.4f}\" ({round(wrap_h * 300)} px @ 300 DPI)")
        print(f"")
        print(f"With buffer:")
        print(f"  Width:  {wrap_w_buffered:.4f}\"")
        print(f"")


if __name__ == "__main__":
    main()
