# Customization

Most scripts in this toolkit work without customization. Two have book-specific patterns that need configuration.

## `docx_to_kindle_epub.py` — book-specific page breaks

If your book has a **dedication** that should sit on its own page, supply the exact opening phrase:

```bash
--dedication-first-line "For my mother"
```

If your book has **back-matter sub-sections** (Glossary, Acknowledgments, Bibliography, etc.) that should each start a fresh page, supply each as a separate flag:

```bash
--back-matter-marker "Glossary" \
--back-matter-marker "Acknowledgments" \
--back-matter-marker "Bibliography" \
--back-matter-marker "About the Author"
```

The pipeline detects bold-text paragraphs matching these markers and promotes them to H2 headings with `page-break-before`.

If you don't supply either flag, the pipeline runs without those transformations — your dedication and back-matter sections rely on whatever page breaks Pandoc inserts by default.

## `generate_back_cover.py` — back cover configuration

The back cover generator reads a JSON config with your book's specific content. Copy `examples/back-cover-config.json` and customize:

```json
{
    "hook": {
        "lines": ["Your hook line one.", "An optional italic second line."],
        "size_pt": 14,
        "italic_line_2": true
    },
    "blurb": [
        "First blurb paragraph.",
        "Second blurb paragraph."
    ],
    "pull_quotes": [
        {"quote": "A pull quote from your book.", "attribution": "From Chapter 1"}
    ],
    "bullets_heading": "Inside this book",
    "bullets": [
        "First key point",
        "Second key point",
        "Third key point"
    ],
    "author_bio": "Your author bio (2-3 sentences).",
    "barcode_position": "bottom-left",
    "barcode_path": "barcode.png",
    "bisac": "Your BISAC Category",
    "price": "$XX.XX USA    $XX.XX CAN",
    "imprint": "Your Imprint Name"
}
```

Then run:

```bash
python scripts/book-publishing/generate_back_cover.py \
  --config back-cover-config.json \
  --output back_generated.png
```

## `validate_metadata.py` — metadata schema

The metadata validator reads a JSON file describing your full KDP metadata. See `examples/metadata-example.json`.

## Font selection

The default body font references in some scripts (`EB Garamond`, Lora) assume those fonts are installed on the system. If you use different fonts, pass them via `--font` flags or edit the script's font path defaults.

Common font choices for trade nonfiction:
- **EB Garamond** — open-source, beautiful, widely used in literary nonfiction
- **Crimson Pro** — open-source, slightly more modern
- **Lora** — open-source, friendly for technical/instructional content
- **Source Serif Pro** — open-source, Adobe-designed, technical-leaning

All four are free from Google Fonts. Install via `apt install fonts-...` or place the TTF/OTF in your system fonts directory.

## Trim size

The default is **5.5 × 8.5 inches** (KDP's most common trade trim). To use a different size, pass `--trim` to each script:

```bash
--trim 6x9      # standard trade paperback
--trim 5x8      # mass-market pocket
--trim 5.25x8   # large mass-market
--trim 6.14x9.21  # KDP "B-format"
```

Spine width and cover wrap dimensions auto-calculate from the trim size + page count.

## Bleed and DPI

The defaults are **0.125" bleed all around** and **300 DPI** — KDP's standard. Override via `--bleed` and `--dpi` if you need IngramSpark's slightly different settings.

## When a script doesn't quite fit your book

These scripts were extracted from a real production pipeline, but every book has edge cases. The most common adjustments:

- **Chapter detection regex** (`docx_to_kindle_epub.py`, function `detect_and_promote_headings`) — add patterns for your chapter naming conventions
- **Callout box keywords** (`docx_to_kindle_epub.py`, function `style_callout_boxes`) — add the heading text your callouts use
- **TOC linkify rules** (`docx_to_kindle_epub.py`, function `linkify_toc_entries`) — tighten or loosen depending on whether your TOC entries follow `"Chapter N Title PageNum"` format

The scripts are intentionally readable Python (not over-engineered) so you can adjust them to your manuscript without spelunking through a framework.

## Pull requests welcome

If you fix a bug or add a useful customization hook, submit a PR. This is a release, not an actively-maintained product — but improvements that help other indie authors are always welcome.
