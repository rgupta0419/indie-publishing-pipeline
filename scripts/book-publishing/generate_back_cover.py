"""
Generate a print-ready back cover from scratch (text + layout configuration).

Produces a single PNG sized to trim dimensions (default 5.5 x 8.5 inches at 300 DPI).
Designed to be paired with `assemble_cover_wrap.py` to build the full wrap.

Layout (top to bottom):
    1. Hook headline (2 lines, italicized 2nd line)
    2. Blurb paragraphs (1-3)
    3. Pull quotes with chapter attribution (0-3)
    4. Author bio (with optional photo to the left)
    5. Barcode zone (configurable: bottom-left or bottom-right)
    6. BISAC categories + price + imprint line

All text rendered with proper margins, line spacing, and font hierarchy.
Black background by default with cream text (override-able).

Usage:
    python generate_back_cover.py \\
        --config back_cover_config.json \\
        --output back_cover.png

    Or with inline overrides:

    python generate_back_cover.py \\
        --hook "Hook line one.|Optional italic line two." \\
        --output back.png

Configuration JSON schema (all fields optional, sensible defaults):
{
    "trim_width": 5.5,
    "trim_height": 8.5,
    "dpi": 300,
    "bg_color": "0,0,0",
    "text_color": "210,195,165",
    "muted_color": "170,155,130",
    "accent_color": "180,140,80",
    "font_serif": "/path/to/serif.ttf",
    "font_italic": "/path/to/italic.ttf",
    "margin_top": 0.4,
    "margin_bottom": 0.4,
    "margin_sides": 0.4,
    "hook": {"lines": ["...", "..."], "size_pt": 20},
    "blurb": ["paragraph 1", "paragraph 2"],
    "pull_quotes": [
        {"quote": "...", "attribution": "From Chapter 1"},
        ...
    ],
    "author_bio": "...",
    "author_photo": null,  // or path to PNG/JPG
    "barcode_position": "bottom-left",  // or "bottom-right"
    "barcode_width_in": 1.47,
    "barcode_height_in": 1.18,
    "barcode_margin_in": 0.55,
    "bisac": "Wisdom Traditions  /  Future Studies",
    "price": "$19.99 USA    $26.99 CAN",
    "imprint": "Your Imprint Name",
    "diya_accent_path": null,  // optional small icon for upper-right corner
}
"""

import argparse
import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont


# ----- Layout defaults (book-content fields are placeholders — supply via --config) -----
DEFAULT_CONFIG = {
    "trim_width": 5.5,
    "trim_height": 8.5,
    "dpi": 300,
    "bg_color": [0, 0, 0],
    "text_color": [210, 195, 165],     # warm cream for body
    "muted_color": [170, 155, 130],    # for chapter attributions
    "accent_color": [248, 227, 192],   # brighter cream for hook + headings
    "font_serif": "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf",
    "font_italic": "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf",
    "margin_top": 0.4,
    "margin_bottom": 0.45,
    "margin_sides": 0.4,
    "hook": {
        "lines": [
            "Your back-cover hook headline.",
            "An optional italic second line."
        ],
        "size_pt": 14,
        "italic_line_2": True,
    },
    "blurb": [
        "Your first blurb paragraph. Replace this placeholder via a --config JSON file "
        "or by editing this list directly.",
        "Your second blurb paragraph.",
    ],
    "pull_quotes": [
        {"quote": "An optional pull quote from your book.",
         "attribution": "From Chapter 1"},
    ],
    "bullets_heading": "Inside this book",
    "bullets": [
        "First bullet — what the reader will get from this book.",
        "Second bullet.",
        "Third bullet.",
    ],
    "timeliness_anchor": None,
    "cta_lines": [
        "Continue at your-website.com — additional resources.",
    ],
    "author_bio": "Your author bio here. Keep it tight (2-3 sentences).",
    "author_photo": None,
    "barcode_position": "bottom-left",
    "barcode_width_in": 1.47,
    "barcode_height_in": 1.18,
    "barcode_margin_in": 0.55,
    "barcode_path": None,         # optional — if provided, gets overlaid
    "bisac": "BISAC Category / Subcategory",
    "price": "$XX.XX USA    $XX.XX CAN",
    "imprint": "Your Imprint Name",
    "diya_accent_path": None,
    "barcode_position": "bottom-right",  # standard for trade nonfiction
    # Layout sizing (pt)
    "blurb_size_pt": 9.5,
    "quote_size_pt": 9.5,
    "attribution_size_pt": 8,
    "bio_size_pt": 9,
    "footer_size_pt": 7.5,
    "bullets_heading_size_pt": 10,
    "bullets_size_pt": 9,
    "cta_size_pt": 9.5,
    "cta_color": [200, 175, 120],
    "timeliness_size_pt": 9,
    "timeliness_color": [170, 155, 130],
    "divider_color": [110, 95, 70],
    "use_dividers": False,
    # Vertical spacing (multiples of line height)
    "section_gap_lines": 0.3,
    "margin_top": 0.35,
    "margin_bottom": 0.35,
    "margin_sides": 0.4,
}


def load_font(path, size_px):
    try:
        return ImageFont.truetype(path, size_px)
    except (IOError, OSError):
        return ImageFont.load_default()


def pt_to_px(pt, dpi):
    return int(pt * dpi / 72)


def wrap_text(text, font, max_width, draw):
    """Word-wrap text to fit max_width."""
    words = text.split()
    if not words:
        return []
    lines, current = [], ""
    for word in words:
        test = (current + " " + word) if current else word
        b = draw.textbbox((0, 0), test, font=font)
        if b[2] - b[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_paragraph(draw, text, font, color, x, y, max_w, line_h):
    """Draw a paragraph, return final y after last line."""
    lines = wrap_text(text, font, max_w, draw)
    for line in lines:
        draw.text((x, y), line, font=font, fill=color)
        y += line_h
    return y


def draw_divider(draw, w, y, color, dpi, char="◆"):
    """Draw a small centered ornamental divider, return next y."""
    # Try using a glyph; if it doesn't render, fall back to short hairline
    from PIL import ImageFont
    try:
        # Use a serif font for glyph
        try:
            f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                                   int(8 * dpi / 72))
        except:
            f = ImageFont.load_default()
        b = draw.textbbox((0, 0), char, font=f)
        gw = b[2] - b[0]
        gh = b[3] - b[1]
        draw.text(((w - gw) // 2, y), char, font=f, fill=color)
        return y + gh + int(0.05 * dpi)
    except Exception:
        line_w = int(0.4 * dpi)
        cx = w // 2
        line_y = y + int(0.05 * dpi)
        draw.line((cx - line_w // 2, line_y, cx + line_w // 2, line_y),
                  fill=color, width=1)
        return y + int(0.15 * dpi)


def render_back_cover(cfg):
    # Convert dimensions
    dpi = cfg["dpi"]
    w = int(cfg["trim_width"] * dpi)
    h = int(cfg["trim_height"] * dpi)
    m_top = int(cfg["margin_top"] * dpi)
    m_bot = int(cfg["margin_bottom"] * dpi)
    m_side = int(cfg["margin_sides"] * dpi)
    content_w = w - 2 * m_side
    bg = tuple(cfg["bg_color"])
    text_c = tuple(cfg["text_color"])
    muted_c = tuple(cfg["muted_color"])
    accent_c = tuple(cfg["accent_color"])

    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    # Pre-load fonts at various sizes
    def f(size_pt, italic=False):
        path = cfg["font_italic"] if italic else cfg["font_serif"]
        return load_font(path, pt_to_px(size_pt, dpi))

    # ===== Diya accent (optional) - upper right corner =====
    if cfg.get("diya_accent_path") and os.path.exists(cfg["diya_accent_path"]):
        accent = Image.open(cfg["diya_accent_path"]).convert("RGBA")
        # Scale to ~0.7" tall
        accent_h_px = int(0.7 * dpi)
        accent_w_px = int(accent.width * (accent_h_px / accent.height))
        accent = accent.resize((accent_w_px, accent_h_px), Image.LANCZOS)
        # Position upper right
        ax = w - m_side // 2 - accent_w_px
        ay = m_top // 4
        img.paste(accent, (ax, ay), accent if accent.mode == "RGBA" else None)

    # ===== Track cursor y =====
    y = m_top

    # ===== Hook =====
    hook = cfg["hook"]
    hook_lines = hook["lines"]
    hook_size = hook.get("size_pt", 20)
    hook_font = f(hook_size, italic=False)
    hook_italic_font = f(hook_size, italic=True)
    hook_line_h = int(pt_to_px(hook_size, dpi) * 1.3)
    for i, line in enumerate(hook_lines):
        font = hook_italic_font if (hook.get("italic_line_2") and i == 1) else hook_font
        draw.text((m_side, y), line, font=font, fill=accent_c)
        y += hook_line_h
    y += int(hook_line_h * cfg["section_gap_lines"])

    # ===== Blurb paragraphs =====
    blurb_font = f(cfg["blurb_size_pt"])
    blurb_italic_font = f(cfg["blurb_size_pt"], italic=True)
    blurb_line_h = int(pt_to_px(cfg["blurb_size_pt"], dpi) * 1.4)
    for para in cfg["blurb"]:
        y = draw_paragraph(draw, para, blurb_font, text_c,
                          m_side, y, content_w, blurb_line_h)
        y += int(blurb_line_h * 0.5)  # paragraph gap
    y += int(blurb_line_h * cfg["section_gap_lines"])

    # ===== Timeliness anchor (italic, muted, single line) =====
    if cfg.get("timeliness_anchor"):
        ta_size = cfg.get("timeliness_size_pt", 9)
        ta_font = f(ta_size, italic=True)
        ta_color = tuple(cfg.get("timeliness_color", [170, 155, 130]))
        ta_line_h = int(pt_to_px(ta_size, dpi) * 1.4)
        ta_lines = wrap_text(cfg["timeliness_anchor"], ta_font, content_w, draw)
        for line in ta_lines:
            draw.text((m_side, y), line, font=ta_font, fill=ta_color)
            y += ta_line_h
        y += int(ta_line_h * cfg["section_gap_lines"])

    # ===== Divider 1 =====
    if cfg.get("use_dividers"):
        y = draw_divider(draw, w, y, tuple(cfg["divider_color"]), dpi)
        y += int(0.05 * dpi)

    # ===== Pull quotes (optional — only renders if list is non-empty) =====
    if cfg.get("pull_quotes"):
        quote_font = f(cfg["quote_size_pt"], italic=True)
        attribution_font = f(cfg["attribution_size_pt"])
        quote_line_h = int(pt_to_px(cfg["quote_size_pt"], dpi) * 1.35)
        attribution_line_h = int(pt_to_px(cfg["attribution_size_pt"], dpi) * 1.3)
        for q in cfg["pull_quotes"]:
            quote_text = f"“{q['quote']}”"
            y = draw_paragraph(draw, quote_text, quote_font, text_c,
                              m_side, y, content_w, quote_line_h)
            attr_text = f"— {q['attribution']}"
            draw.text((m_side, y), attr_text, font=attribution_font, fill=muted_c)
            y += attribution_line_h
            y += int(quote_line_h * 0.45)
        y += int(quote_line_h * cfg["section_gap_lines"])

    # ===== Divider 2 =====
    if cfg.get("use_dividers"):
        y = draw_divider(draw, w, y, tuple(cfg["divider_color"]), dpi)
        y += int(0.05 * dpi)

    # ===== "Inside this book" bullets =====
    if cfg.get("bullets"):
        # Section heading
        bh_size = cfg.get("bullets_heading_size_pt", 11)
        bh_font = f(bh_size, italic=True)
        bh_line_h = int(pt_to_px(bh_size, dpi) * 1.4)
        draw.text((m_side, y), cfg.get("bullets_heading", "Inside this book"),
                  font=bh_font, fill=accent_c)
        y += bh_line_h + int(bh_line_h * 0.15)

        # Bullets
        b_size = cfg.get("bullets_size_pt", 10)
        b_font = f(b_size)
        b_line_h = int(pt_to_px(b_size, dpi) * 1.35)
        bullet_char = "•"  # standard bullet (well-supported)
        bullet_indent_px = int(0.25 * dpi)
        bullet_text_x = m_side + bullet_indent_px
        bullet_text_w = content_w - bullet_indent_px
        for bullet in cfg["bullets"]:
            # Draw bullet char
            draw.text((m_side + int(0.05 * dpi), y), bullet_char,
                      font=b_font, fill=tuple(cfg.get("cta_color", [200, 175, 120])))
            # Wrap and draw bullet text
            lines = wrap_text(bullet, b_font, bullet_text_w, draw)
            for i, line in enumerate(lines):
                draw.text((bullet_text_x, y), line, font=b_font, fill=text_c)
                y += b_line_h
            y += int(b_line_h * 0.25)  # gap between bullets
        y += int(b_line_h * cfg["section_gap_lines"])

    # ===== Reserve bottom area for barcode + footer =====
    bc_w_px = int(cfg["barcode_width_in"] * dpi)
    bc_h_px = int(cfg["barcode_height_in"] * dpi)
    bc_margin_px = int(cfg["barcode_margin_in"] * dpi)
    footer_font = f(cfg["footer_size_pt"])
    footer_line_h = int(pt_to_px(cfg["footer_size_pt"], dpi) * 1.5)
    # Total bottom-reserved height = barcode height + small gap + footer
    bottom_reserved = bc_h_px + bc_margin_px + footer_line_h
    bottom_zone_top = h - bottom_reserved - m_bot // 2

    # ===== Author bio (positioned in space between pull quotes and bottom zone) =====
    available_for_bio = bottom_zone_top - y
    bio_font = f(cfg["bio_size_pt"])
    bio_line_h = int(pt_to_px(cfg["bio_size_pt"], dpi) * 1.4)

    # If photo, render to the left, bio to the right; else bio full width
    photo_path = cfg.get("author_photo")
    if photo_path and os.path.exists(photo_path):
        # Photo size ~1.4 inches square, anchored at bio's left
        photo_size_px = int(1.4 * dpi)
        photo = Image.open(photo_path).convert("RGB").resize(
            (photo_size_px, photo_size_px), Image.LANCZOS
        )
        photo_x = m_side
        photo_y = y
        img.paste(photo, (photo_x, photo_y))
        bio_text_x = photo_x + photo_size_px + int(0.2 * dpi)
        bio_text_max_w = w - m_side - bio_text_x
    else:
        bio_text_x = m_side
        bio_text_max_w = content_w

    bio_y = y
    bio_y = draw_paragraph(draw, cfg["author_bio"], bio_font, text_c,
                           bio_text_x, bio_y, bio_text_max_w, bio_line_h)

    # ===== CTA — drives readers to yatubook.com =====
    if cfg.get("cta_lines"):
        cta_size = cfg.get("cta_size_pt", 10)
        cta_font_main = f(cta_size, italic=False)
        cta_font_sub = f(max(cta_size - 1, 8))
        cta_line_h = int(pt_to_px(cta_size, dpi) * 1.4)
        cta_color = tuple(cfg.get("cta_color", [200, 175, 120]))

        # Compute total CTA block height first
        cta_total_h = 0
        cta_pre_rendered = []  # (font, color, lines)
        for i, line in enumerate(cfg["cta_lines"]):
            font_to_use = cta_font_main if i == 0 else cta_font_sub
            color_to_use = cta_color if i == 0 else text_c
            lines = wrap_text(line, font_to_use, content_w, draw)
            cta_pre_rendered.append((font_to_use, color_to_use, lines))
            cta_total_h += len(lines) * cta_line_h

        # Anchor CTA to just above the barcode top, with breathing room
        # Always render at the anchor position (don't follow bio) — bio gets squeezed
        # if it overflows, which is the right tradeoff (CTA matters more for marketing)
        cta_top_anchor = (h - m_bot // 2 - bc_h_px - footer_line_h) - cta_total_h - int(0.18 * dpi)
        cta_y = cta_top_anchor
        for font_to_use, color_to_use, lines in cta_pre_rendered:
            for sub in lines:
                draw.text((m_side, cta_y), sub, font=font_to_use, fill=color_to_use)
                cta_y += cta_line_h

    # ===== Barcode zone (bottom-left or bottom-right) =====
    bc_y = h - m_bot // 2 - bc_h_px - footer_line_h
    if cfg["barcode_position"] == "bottom-left":
        bc_x = m_side
    else:
        bc_x = w - m_side - bc_w_px

    # Optionally overlay actual barcode image, else draw placeholder rectangle
    bc_path = cfg.get("barcode_path")
    if bc_path and os.path.exists(bc_path):
        barcode = Image.open(bc_path).convert("RGB").resize(
            (bc_w_px, bc_h_px), Image.LANCZOS
        )
        img.paste(barcode, (bc_x, bc_y))
    else:
        # Placeholder white rectangle with "BARCODE" label
        draw.rectangle((bc_x, bc_y, bc_x + bc_w_px, bc_y + bc_h_px),
                       fill=(255, 255, 255), outline=(80, 80, 80), width=2)
        placeholder_font = f(11)
        plabel = "BARCODE"
        pb = draw.textbbox((0, 0), plabel, font=placeholder_font)
        draw.text((bc_x + (bc_w_px - (pb[2]-pb[0]))//2,
                   bc_y + (bc_h_px - (pb[3]-pb[1]))//2),
                  plabel, font=placeholder_font, fill=(80, 80, 80))

    # ===== Footer (BISAC + price + imprint) =====
    # Goes to the OPPOSITE side of the barcode, vertically centered against barcode
    if cfg["barcode_position"] == "bottom-left":
        footer_x = bc_x + bc_w_px + int(0.3 * dpi)
        footer_align_right = False
    else:
        footer_x = m_side
        footer_align_right = False

    footer_y = bc_y + int(0.2 * dpi)
    for line, line_text in [
        ("bisac", cfg["bisac"]),
        ("price", cfg["price"]),
        ("imprint", cfg["imprint"]),
    ]:
        if line_text:
            draw.text((footer_x, footer_y), line_text,
                      font=footer_font, fill=text_c if line != "imprint" else muted_c)
            footer_y += footer_line_h

    return img


def main():
    p = argparse.ArgumentParser(description="Generate print-ready back cover PNG")
    p.add_argument("--config", help="JSON config file (overrides defaults)")
    p.add_argument("--output", required=True, help="Output PNG path")
    p.add_argument("--photo", help="Author photo path (overrides config)")
    p.add_argument("--barcode", help="Barcode image path (overrides config)")
    p.add_argument("--barcode-position", choices=["bottom-left", "bottom-right"],
                   help="Barcode position (overrides config)")
    p.add_argument("--diya-accent", help="Diya icon for upper-right corner")
    args = p.parse_args()

    cfg = dict(DEFAULT_CONFIG)
    if args.config and os.path.exists(args.config):
        with open(args.config) as fp:
            cfg.update(json.load(fp))

    if args.photo:
        cfg["author_photo"] = args.photo
    if args.barcode:
        cfg["barcode_path"] = args.barcode
    if args.barcode_position:
        cfg["barcode_position"] = args.barcode_position
    if args.diya_accent:
        cfg["diya_accent_path"] = args.diya_accent

    img = render_back_cover(cfg)
    img.save(args.output)
    print(f"Generated: {args.output}")
    print(f"  Dimensions: {img.size[0]} × {img.size[1]} px "
          f"({img.size[0]/cfg['dpi']:.2f} × {img.size[1]/cfg['dpi']:.2f} inches "
          f"at {cfg['dpi']} DPI)")


if __name__ == "__main__":
    main()
