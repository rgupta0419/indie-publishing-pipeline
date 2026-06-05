# Indie Book Publishing Pipeline

**Open-source toolkit for self-published authors using KDP, IngramSpark, and other print-on-demand services.**

> **First time here? Read [STORY.md](./STORY.md) first.** It tells the full story of why this toolkit exists — the publisher quotes ($200 vanity packages with three cover options, Reedsy at $8,000), the Reddit horror stories, and the 15 specific production problems hit during a real book launch. Each script in this repo solves one of them.
>
> **Hit a specific KDP error?** Jump to [FAQ.md](./FAQ.md). Common problems with exact fixes — broken TOC link rejection, spine text too close to edges, A+ Content newline limits, BISAC code selection, and more.
>
> **Trying to figure out if this is for you?** See [USE_CASES.md](./USE_CASES.md). Eight specific author profiles (first-time nonfiction, spiritual/self-help, illustrated books, rejected-by-KDP, deadline-driven, developer-leaning, vanity-press-suspicious, cost-comparing) with the exact toolkit features that map to each.
>
> **Forking this and want to push it as your own repo?** See [SETUP.md](./SETUP.md) for the git-init / GitHub push sequence.

Battle-tested on a 60,000-word nonfiction title — [YATU: You Are the Upgrade](https://www.amazon.com/dp/B0H38DZDS5), released June 2026 at [yatubook.com](https://yatubook.com) — with 14 illustrations, 95 footnotes, complex back-matter, and a print + Kindle ebook release. Takes a `.docx` manuscript and a cover design and produces the exact files KDP requires — interior PDF, cover wrap PDF, Kindle EPUB — with validation at every stage.

---

## What's in here

**15 Python scripts** organized into two pipelines:

- **`scripts/book-publishing/`** — the production pipeline (11 scripts). Reflows a master manuscript into trade trim format, adds running headers and page numbers, audits for widows/orphans, generates back cover art, assembles the cover wrap, and produces a Kindle EPUB.
- **`scripts/kdp-publishing/`** — KDP-specific validators (4 scripts). Pre-flight checks for cover dimensions, interior PDF, metadata, and spine width calculation. Catches issues locally before uploading to KDP, where each rejection costs 24–72 hours.

Plus:

- **`docs/`** — overview of the pipeline, stage-by-stage guide, customization notes
- **`examples/`** — sample config files for the parameterized scripts
- **`LICENSE`** — MIT (free for commercial use; attribution requested)

---

## Quickstart — Kindle EPUB

If you already have a polished `.docx` manuscript and a 1600 × 2560 cover JPG:

```bash
pip install pypdf python-docx pillow
sudo apt install pandoc        # or: brew install pandoc

python scripts/book-publishing/docx_to_kindle_epub.py \
  --input manuscript.docx \
  --cover ebook_cover.jpg \
  --output mybook.epub \
  --title "Your Book Title" \
  --subtitle "Your Subtitle" \
  --author "Author Name" \
  --isbn "978-X-XXXXXXX-X-X" \
  --publisher "Your Imprint"
```

Then preview the result:

```bash
python scripts/book-publishing/epub_reviewer.py mybook.epub --output review/
# Open review/index.html in your browser
```

The pipeline runs ~12 transformations under the hood: smart quote conversion, heading auto-detection, chapter splitting, callout box styling, page break management, TOC linking, navigation file generation. See `docs/ebook-pipeline.md` for the full list.

---

## Quickstart — Print paperback cover wrap

If you have separate front cover, back cover, and spine images at the right dimensions:

```bash
python scripts/kdp-publishing/recalc_spine.py 250    # get spine width for 250 pages

python scripts/book-publishing/assemble_cover_wrap.py \
  --front front_cover.png \
  --back back_cover.png \
  --spine-image spine.png \
  --output cover_wrap.pdf \
  --spine-width 0.625    # value from recalc_spine

python scripts/kdp-publishing/validate_cover.py \
  cover_wrap.pdf --trim 5.5x8.5 --pages 250
```

The validator confirms dimensions match KDP's expected wrap before you upload. See `docs/print-pipeline.md` for the full stage-by-stage flow.

---

## Why this exists

Most indie publishing guides assume you'll either pay a service to handle production or use the manual KDP web tools (which are slow, error-prone, and don't catch common rejection-triggering issues until KDP rejects you 24–72 hours later).

This toolkit was built during a real book launch in 2026. Every script was written to solve a problem that came up during production:

- Pandoc's docx → EPUB conversion drops chapter structure → `docx_to_kindle_epub.py` rebuilds it
- KDP's "broken TOC link" rejection comes from cross-file anchors → the pipeline fixes them automatically
- Spine text running into the cover edges → `assemble_cover_wrap.py` handles safety margins
- Manuscript page count shifts → `recalc_spine.py` recomputes the spine width instantly
- Widows and orphans in the print PDF → `audit_cx.py` flags them, `fix_orphans.py` fixes them surgically

Each problem was hit, debugged, and solved during production. The fixes are now in the pipeline so other authors don't hit them.

---

## Requirements

- Python 3.10+
- `pandoc` (system package) — required by `docx_to_kindle_epub.py`
- Python packages: `pypdf`, `python-docx`, `Pillow`
- Optional: `libreoffice` (used by some print-pipeline stages for docx → PDF conversion)

---

## Customization

Most scripts work out-of-the-box for any book. A few have book-specific patterns that need configuration:

- `docx_to_kindle_epub.py` — supports `--dedication-first-line` and `--back-matter-marker` flags so the pipeline knows where to insert page breaks for your specific book. See `examples/example-book-config.md`.
- `generate_back_cover.py` — reads a JSON config file with your blurb, pull quotes, author bio, BISAC code, and barcode position. See `examples/back-cover-config.json`.

All other scripts run with their defaults (KDP standard 5.5 × 8.5 trim, 0.125" bleed, 300 DPI) and only need command-line arguments specific to your book.

---

## License

MIT. Free for commercial use. Attribution requested but not required.

---

## Origin

This toolkit was extracted from the production pipeline of [YATU: You Are the Upgrade](https://www.amazon.com/dp/B0H38DZDS5), a 2026 nonfiction book published via Kindle Direct Publishing. The original author maintains a private fork for his own books; this public release is the same code with all book-specific content (titles, author names, ISBNs, manuscript-specific text patterns) replaced with parameterized inputs.

The full story of the production — what went wrong, what got fixed, what costs were avoided, and why this is being released — is in [STORY.md](./STORY.md). It's long, but if you're an indie author trying to decide between Reedsy and the vanity-press path, it's worth reading before you commit.

If the toolkit helps you publish your own book, that's the only thanks needed. If you find and fix bugs, pull requests are welcome — but this is a release, not an actively-maintained product.

## Useful links

- **The book this came from:** [YATU on Amazon](https://www.amazon.com/dp/B0H38DZDS5) (paperback + Kindle)
- **The author's site:** [yatubook.com](https://yatubook.com)
- **Substack:** [jyolingapp.substack.com](https://jyolingapp.substack.com)
- **X / Twitter:** [@jyolingapp](https://x.com/jyolingapp)
