"""
Stage 6 — Assemble full cover wrap PDF from front + back cover images, with spine + barcode.

Produces a KDP-ready cover wrap PDF at exact dimensions:
  width  = 2 * trim_width + spine_width + 2 * bleed
  height = trim_height + 2 * bleed

Layout (left to right when laid flat):
  [back cover (with bleed left, trim, half-spine)]
  [spine (solid bg + rotated text)]
  [front cover (half-spine, trim, bleed right)]

Spine includes text rotated 90° clockwise (US convention — reads top-to-bottom
when book is shelved spine-up):
  - Top: author name (small caps, tracked)
  - Middle: title (large display)
  - Below title: subtitle (italic, smaller)
  - Bottom: publisher (small caps, tracked)

Barcode is overlaid on the back cover (bottom-right when viewed alone), with
a white rectangle UNDER the barcode for scanner-compatible white background.

Input cover images should be exactly trim-size (5.5 × 8.5 inches at 300 DPI =
1650 × 2550 pixels typical). Script auto-extends bleed by edge-replication.

If your cover images include bleed already (5.75 × 8.75 inches at 300 DPI =
1725 × 2625 pixels), pass --no-bleed-add to skip the extension.

Usage:
    python assemble_cover_wrap.py \\
        --front front_cover.png \\
        --back back_cover.png \\
        --barcode barcode.png \\
        --output cover_wrap_FINAL.pdf \\
        --spine-width 0.552 \\
        --spine-bg-color "0,10,40" \\
        --spine-text-color "245,232,200" \\
        --title "Your Book Title" \\
        --subtitle "Your Subtitle" \\
        --author "AUTHOR NAME" \\
        --publisher "YOUR IMPRINT"
"""

import argparse
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps


def parse_color(s):
    """Parse 'R,G,B' string to tuple."""
    return tuple(int(x.strip()) for x in s.split(','))


def find_font(font_names, size):
    """Try to find a font on the system. Falls back to default if none found."""
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
        '/System/Library/Fonts/Georgia.ttf',
        '/System/Library/Fonts/Times.ttc',
    ]
    if font_names:
        if isinstance(font_names, str):
            font_names = [font_names]
        candidates = font_names + candidates
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def extend_bleed(img, bleed_px, sides='all'):
    """Extend image bleed by replicating edge pixels.

    sides: 'all', 'top_bottom' (no left/right bleed), or list of sides
    """
    w, h = img.size
    if sides == 'all':
        new_img = Image.new('RGB', (w + 2*bleed_px, h + 2*bleed_px))
        # Place original in center
        new_img.paste(img, (bleed_px, bleed_px))
        # Replicate top edge
        top_strip = img.crop((0, 0, w, 1)).resize((w, bleed_px))
        new_img.paste(top_strip, (bleed_px, 0))
        # Bottom edge
        bot_strip = img.crop((0, h-1, w, h)).resize((w, bleed_px))
        new_img.paste(bot_strip, (bleed_px, h + bleed_px))
        # Left edge
        left_strip = img.crop((0, 0, 1, h)).resize((bleed_px, h))
        new_img.paste(left_strip, (0, bleed_px))
        # Right edge
        right_strip = img.crop((w-1, 0, w, h)).resize((bleed_px, h))
        new_img.paste(right_strip, (w + bleed_px, bleed_px))
        # Corners — replicate corner pixels
        for x, y, src_x, src_y in [
            (0, 0, 0, 0),                                            # top-left
            (w + bleed_px, 0, w-1, 0),                               # top-right
            (0, h + bleed_px, 0, h-1),                                # bot-left
            (w + bleed_px, h + bleed_px, w-1, h-1),                   # bot-right
        ]:
            corner_pixel = img.getpixel((src_x, src_y))
            corner_box = Image.new('RGB', (bleed_px, bleed_px), corner_pixel)
            new_img.paste(corner_box, (x, y))
        return new_img
    elif sides == 'top_bottom':
        new_img = Image.new('RGB', (w, h + 2*bleed_px))
        new_img.paste(img, (0, bleed_px))
        top_strip = img.crop((0, 0, w, 1)).resize((w, bleed_px))
        new_img.paste(top_strip, (0, 0))
        bot_strip = img.crop((0, h-1, w, h)).resize((w, bleed_px))
        new_img.paste(bot_strip, (0, h + bleed_px))
        return new_img
    return img


def build_spine(spine_w_px, spine_h_px, bg_color, text_color,
                title, subtitle, author, publisher, font_paths=None):
    """Build the spine as a vertical PIL image with rotated text.

    spine_h_px includes top+bottom bleed.
    """
    spine = Image.new('RGB', (spine_w_px, spine_h_px), bg_color)

    # Build text in a HORIZONTAL canvas, then rotate 90° clockwise
    # When rotated CW, what was horizontal becomes vertical reading top-to-bottom
    txt_w = spine_h_px   # the longer dimension becomes width
    txt_h = spine_w_px   # spine width becomes the height
    text_canvas = Image.new('RGB', (txt_w, txt_h), bg_color)
    draw = ImageDraw.Draw(text_canvas)

    # Font sizes proportional to spine width
    # For 0.552" spine at 300 DPI = 166px spine width
    title_size = max(int(spine_w_px * 0.45), 12)
    subtitle_size = max(int(spine_w_px * 0.18), 8)
    author_size = max(int(spine_w_px * 0.13), 7)
    publisher_size = max(int(spine_w_px * 0.10), 6)

    title_font = find_font(font_paths, title_size)
    subtitle_font = find_font(font_paths, subtitle_size)
    author_font = find_font(font_paths, author_size)
    publisher_font = find_font(font_paths, publisher_size)

    # Layout positions (in horizontal canvas coords, which become vertical after rotation)
    # txt_w is the spine LENGTH (was height), txt_h is spine THICKNESS (was width)
    # Center vertically (in spine thickness)
    cy = txt_h // 2

    # AUTHOR — near top of spine (left edge of horizontal canvas before rotation)
    author_text = author.upper()
    author_bbox = draw.textbbox((0, 0), author_text, font=author_font)
    author_w_text = author_bbox[2] - author_bbox[0]
    author_h_text = author_bbox[3] - author_bbox[1]
    draw.text(
        (int(txt_w * 0.08), cy - author_h_text // 2),
        author_text, fill=text_color, font=author_font
    )

    # TITLE — center of spine
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w_text = title_bbox[2] - title_bbox[0]
    title_h_text = title_bbox[3] - title_bbox[1]
    draw.text(
        ((txt_w - title_w_text) // 2, cy - title_h_text // 2 - title_bbox[1]),
        title, fill=text_color, font=title_font
    )

    # SUBTITLE — just below title (visually) — but in horizontal canvas, just to the right of title
    if subtitle:
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_w_text = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (txt_w + title_w_text) // 2 + int(spine_w_px * 0.15)
        if subtitle_x + subtitle_w_text < txt_w * 0.85:
            draw.text(
                (subtitle_x, cy - (subtitle_bbox[3] - subtitle_bbox[1]) // 2),
                subtitle, fill=text_color, font=subtitle_font
            )

    # PUBLISHER — near bottom of spine (right edge of horizontal canvas)
    publisher_text = publisher.upper()
    publisher_bbox = draw.textbbox((0, 0), publisher_text, font=publisher_font)
    publisher_w_text = publisher_bbox[2] - publisher_bbox[0]
    publisher_h_text = publisher_bbox[3] - publisher_bbox[1]
    draw.text(
        (int(txt_w * 0.92) - publisher_w_text, cy - publisher_h_text // 2),
        publisher_text, fill=text_color, font=publisher_font
    )

    # Rotate 90° clockwise — text now reads top-to-bottom
    spine = text_canvas.rotate(-90, expand=True)

    return spine


def overlay_barcode_on_back(back_img, barcode_path,
                            barcode_width_in=1.47, barcode_height_in=1.18,
                            dpi=300, margin_in=0.25, white_bg_padding_in=0.15,
                            right_margin_in=None, bottom_margin_in=None,
                            skip_white_bg=False):
    """Overlay barcode on the back cover.

    Position: bottom-right corner of back cover (when viewed alone).
    Adds a white rectangle UNDER the barcode for scanner contrast on dark covers.

    Returns modified back_img.
    """
    back_w, back_h = back_img.size

    # Load barcode
    barcode = Image.open(barcode_path).convert('RGB')

    # Resize barcode to target print dimensions
    bc_w_px = int(barcode_width_in * dpi)
    bc_h_px = int(barcode_height_in * dpi)
    barcode = barcode.resize((bc_w_px, bc_h_px), Image.LANCZOS)

    # White background rectangle dimensions (slightly larger than barcode)
    pad_px = int(white_bg_padding_in * dpi)
    bg_w = bc_w_px + 2 * pad_px
    bg_h = bc_h_px + 2 * pad_px

    # Position — use right_margin_in / bottom_margin_in if provided, else margin_in
    right_margin_px = int((right_margin_in if right_margin_in is not None else margin_in) * dpi)
    bottom_margin_px = int((bottom_margin_in if bottom_margin_in is not None else margin_in) * dpi)

    if skip_white_bg:
        # No white rectangle — place barcode directly (cover already has placeholder)
        bc_x = back_w - bc_w_px - right_margin_px
        bc_y = back_h - bc_h_px - bottom_margin_px
        back_img.paste(barcode, (bc_x, bc_y))
    else:
        bg_x = back_w - bg_w - right_margin_px
        bg_y = back_h - bg_h - bottom_margin_px
        white_bg = Image.new('RGB', (bg_w, bg_h), (255, 255, 255))
        back_img.paste(white_bg, (bg_x, bg_y))
        bc_x = bg_x + pad_px
        bc_y = bg_y + pad_px
        back_img.paste(barcode, (bc_x, bc_y))

    return back_img


def assemble_cover_wrap(
    front_path, back_path, barcode_path, output_path,
    trim_w=5.5, trim_h=8.5, spine_w=0.552, bleed=0.125, dpi=300,
    add_bleed=True,
    spine_bg=(10, 22, 40), spine_text=(245, 232, 200),
    title='', subtitle='',
    author='', publisher='',
    font_paths=None,
    barcode_w_in=1.47, barcode_h_in=1.18,
    spine_image_path=None,
    spine_crop_to_center=False,
    barcode_right_margin_in=None,
    barcode_bottom_margin_in=None,
    barcode_skip_white_bg=False,
):
    """Main assembly function."""
    # Convert dimensions to pixels
    trim_w_px = int(trim_w * dpi)
    trim_h_px = int(trim_h * dpi)
    spine_w_px = int(spine_w * dpi)
    bleed_px = int(bleed * dpi)

    # Total wrap dimensions
    total_w_px = 2 * trim_w_px + spine_w_px + 2 * bleed_px
    total_h_px = trim_h_px + 2 * bleed_px

    print(f"Cover wrap dimensions: {total_w_px} × {total_h_px} pixels "
          f"({total_w_px/dpi:.3f} × {total_h_px/dpi:.3f} inches at {dpi} DPI)")

    # Load back cover
    print(f"Loading back cover: {back_path}")
    back = Image.open(back_path).convert('RGB')
    back_orig_size = back.size
    print(f"  Original: {back_orig_size[0]} × {back_orig_size[1]} px "
          f"= {back_orig_size[0]/dpi:.2f} × {back_orig_size[1]/dpi:.2f} inches")

    # Resize back to exact trim size
    back = back.resize((trim_w_px, trim_h_px), Image.LANCZOS)

    # Overlay barcode on back cover (only if barcode path provided)
    if barcode_path:
        print(f"Overlaying barcode on back cover")
        back = overlay_barcode_on_back(
            back, barcode_path,
            barcode_width_in=barcode_w_in, barcode_height_in=barcode_h_in,
            dpi=dpi,
            right_margin_in=barcode_right_margin_in,
            bottom_margin_in=barcode_bottom_margin_in,
            skip_white_bg=barcode_skip_white_bg,
        )
    else:
        print(f"No barcode path provided — assuming back cover already has barcode embedded")

    # Load front cover
    print(f"Loading front cover: {front_path}")
    front = Image.open(front_path).convert('RGB')
    front_orig_size = front.size
    print(f"  Original: {front_orig_size[0]} × {front_orig_size[1]} px "
          f"= {front_orig_size[0]/dpi:.2f} × {front_orig_size[1]/dpi:.2f} inches")
    front = front.resize((trim_w_px, trim_h_px), Image.LANCZOS)

    # Build spine — use pre-designed image if provided, else build programmatically
    spine_total_h_px = trim_h_px + 2 * bleed_px  # spine extends full height with bleed
    if spine_image_path:
        print(f"Loading pre-designed spine: {spine_image_path}")
        spine = Image.open(spine_image_path).convert('RGB')
        sw_orig, sh_orig = spine.size
        print(f"  Original: {sw_orig} × {sh_orig} px "
              f"= {sw_orig/dpi:.2f} × {sh_orig/dpi:.2f} inches at {dpi} DPI")
        if spine_crop_to_center:
            # Crop the central spine_w_px strip out of a wider image
            # (handles case where spine artwork has black padding on both sides)
            target_aspect = spine_w_px / spine_total_h_px
            current_aspect = sw_orig / sh_orig
            if current_aspect > target_aspect:
                # Wider than needed — crop horizontally from center
                new_w = int(sh_orig * target_aspect)
                left = (sw_orig - new_w) // 2
                spine = spine.crop((left, 0, left + new_w, sh_orig))
                print(f"  Cropped center column: {new_w} × {sh_orig} px")
        spine = spine.resize((spine_w_px, spine_total_h_px), Image.LANCZOS)
        print(f"  Resized to spine slot: {spine_w_px} × {spine_total_h_px} px")
    else:
        print(f"Building spine programmatically ({spine_w}\" wide)")
        spine = build_spine(
            spine_w_px, spine_total_h_px,
            spine_bg, spine_text,
            title, subtitle, author, publisher,
            font_paths=font_paths
        )

    # Compose full wrap
    print(f"Composing full wrap")
    wrap = Image.new('RGB', (total_w_px, total_h_px), spine_bg)

    if add_bleed:
        # Back cover gets bleed on left, top, bottom (no bleed on right — spine handles it)
        back_with_bleed = extend_bleed(back, bleed_px, sides='all')
        # Trim the right bleed since spine handles that side
        back_with_bleed = back_with_bleed.crop(
            (0, 0, back_with_bleed.width - bleed_px, back_with_bleed.height)
        )
        wrap.paste(back_with_bleed, (0, 0))

        # Place spine in middle (after back with its bleed)
        spine_x = back_with_bleed.width
        wrap.paste(spine, (spine_x, 0))

        # Front cover gets bleed on right, top, bottom (no bleed on left — spine handles it)
        front_with_bleed = extend_bleed(front, bleed_px, sides='all')
        front_with_bleed = front_with_bleed.crop(
            (bleed_px, 0, front_with_bleed.width, front_with_bleed.height)
        )
        wrap.paste(front_with_bleed, (spine_x + spine_w_px, 0))
    else:
        # Covers already include bleed
        wrap.paste(back, (0, 0))
        wrap.paste(spine, (back.width, bleed_px))
        wrap.paste(front, (back.width + spine.width, 0))

    # Save as PDF
    print(f"Saving PDF: {output_path}")
    wrap.save(output_path, 'PDF', resolution=dpi)

    # Stats
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"\n=== DONE ===")
    print(f"Output: {output_path}")
    print(f"Size: {size_mb:.1f} MB")
    print(f"Dimensions: {total_w_px} × {total_h_px} px @ {dpi} DPI")
    print(f"Print size: {total_w_px/dpi:.3f} × {total_h_px/dpi:.3f} inches")


def main():
    p = argparse.ArgumentParser(description="Assemble KDP-ready cover wrap PDF")
    p.add_argument("--front", required=True, help="Front cover image (PNG/JPG)")
    p.add_argument("--back", required=True, help="Back cover image (PNG/JPG)")
    p.add_argument("--barcode", default=None, help="ISBN barcode image (PNG). "
                   "If omitted, no barcode overlay is added (use when back cover "
                   "image already has the barcode embedded).")
    p.add_argument("--output", required=True, help="Output PDF path")
    p.add_argument("--trim-width", type=float, default=5.5, help="Trim width (inches)")
    p.add_argument("--trim-height", type=float, default=8.5, help="Trim height (inches)")
    p.add_argument("--spine-width", type=float, default=0.552, help="Spine width (inches)")
    p.add_argument("--bleed", type=float, default=0.125, help="Bleed (inches)")
    p.add_argument("--dpi", type=int, default=300, help="Output DPI")
    p.add_argument("--no-bleed-add", action="store_true",
                   help="Skip bleed extension (cover images already include bleed)")
    p.add_argument("--spine-bg-color", default="10,22,40",
                   help="Spine background RGB (e.g. '10,22,40' for dark navy)")
    p.add_argument("--spine-text-color", default="245,232,200",
                   help="Spine text RGB (e.g. '245,232,200' for cream)")
    p.add_argument("--title", default="")
    p.add_argument("--subtitle", default="")
    p.add_argument("--author", default="RANJAN GUPTA")
    p.add_argument("--publisher", default="JYOLING PRESS")
    p.add_argument("--font", action="append", default=[],
                   help="Specific font file paths to try (repeatable)")
    p.add_argument("--barcode-width", type=float, default=1.47,
                   help="Barcode width (inches, standard EAN-13 = 1.47)")
    p.add_argument("--barcode-height", type=float, default=1.18,
                   help="Barcode height (inches)")
    p.add_argument("--spine-image", default=None,
                   help="Pre-designed spine image (PNG/JPG). If provided, used "
                        "instead of programmatic spine generation.")
    p.add_argument("--spine-crop-to-center", action="store_true",
                   help="If --spine-image is wider than needed, crop the "
                        "center column (use when spine artwork has black "
                        "padding flanking the actual spine strip).")
    p.add_argument("--barcode-right-margin", type=float, default=None,
                   help="Barcode distance from right edge of back cover (inches). "
                        "Overrides default 0.25 inch.")
    p.add_argument("--barcode-bottom-margin", type=float, default=None,
                   help="Barcode distance from bottom edge of back cover (inches). "
                        "Overrides default 0.25 inch.")
    p.add_argument("--barcode-skip-white-bg", action="store_true",
                   help="Skip the white background rectangle behind the barcode "
                        "(use when back cover already has a placeholder rectangle "
                        "designed in).")
    args = p.parse_args()

    assemble_cover_wrap(
        args.front, args.back, args.barcode, args.output,
        trim_w=args.trim_width,
        trim_h=args.trim_height,
        spine_w=args.spine_width,
        bleed=args.bleed,
        dpi=args.dpi,
        add_bleed=not args.no_bleed_add,
        spine_bg=parse_color(args.spine_bg_color),
        spine_text=parse_color(args.spine_text_color),
        title=args.title,
        subtitle=args.subtitle,
        author=args.author,
        publisher=args.publisher,
        font_paths=args.font if args.font else None,
        barcode_w_in=args.barcode_width,
        barcode_h_in=args.barcode_height,
        spine_image_path=args.spine_image,
        spine_crop_to_center=args.spine_crop_to_center,
        barcode_right_margin_in=args.barcode_right_margin,
        barcode_bottom_margin_in=args.barcode_bottom_margin,
        barcode_skip_white_bg=args.barcode_skip_white_bg,
    )


if __name__ == "__main__":
    main()
