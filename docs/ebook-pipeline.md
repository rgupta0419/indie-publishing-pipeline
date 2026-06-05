# Kindle EPUB pipeline — `docx_to_kindle_epub.py`

Takes a polished `.docx` manuscript and produces a KDP-ready Kindle EPUB. Single command, ~12 transformations under the hood. Output validates with the KDP previewer and passes Amazon's cover/TOC checks.

## What it does

| Stage | Transformation |
|---|---|
| 1 | Pandoc converts docx → EPUB 3 base |
| 2 | Smart-quote conversion — converts straight `'` `"` to curly `'` `"` everywhere except inside HTML attribute values |
| 3 | Heading auto-detection — finds chapter markers (`Chapter 1`, `PROLOGUE`, `PART I`, `AUTHOR'S NOTE`, etc.) in paragraphs and promotes them to `<h1>` / `<h2>` |
| 4 | Chapter title class-tagging — tags Part subtitles and chapter subtitle lines so the CSS can style them |
| 5 | Dedication page break — if `--dedication-first-line` is supplied, inserts a clean page break before the dedication |
| 5a | Back-matter section promotion — if `--back-matter-marker` flags are supplied, promotes those bold-text sections to H2 with page breaks (Glossary, Acknowledgments, Lineage, etc.) |
| 5b | Chapter illustration isolation — places `<p><img/></p>` elements that sit before chapter headings on their own dedicated page (clean opener look) |
| 6 | TOC linkification — wraps chapter entries in the visible CONTENTS page as `<a href>` links to the chapter anchors |
| 7 | Callout box styling — wraps tables (used as sidebars / call-outs in the source docx) with `class="callout"` |
| 8 | Figure wrapping — wraps orphan `<img>` tags in `<figure>` |
| 9 | Section break normalization — converts `———` and `* * *` markers to proper centered scene breaks |
| 10 | Section tag balancing — order-aware fix for orphan `</section>` tags that would otherwise break the XHTML parser |
| 11 | Title page cleanup — replaces the messy Pandoc title-page duplication with a clean title-page div |
| 12 | Chapter splitting — splits the monolithic generated XHTML into per-chapter files at H1 boundaries |
| 13 | Cross-file anchor rewriting — converts `<a href="#chapter-N">` links to `<a href="filename.xhtml#chapter-N">` so they resolve across the split files (this fix is what catches KDP's "broken TOC link" rejection) |
| 14 | Navigation rebuild — generates `nav.xhtml` (EPUB 3) and `toc.ncx` (EPUB 2 fallback) with real chapter entries extracted from the split files' first H1s |
| 15 | CSS injection — adds Kindle-optimized stylesheet to every XHTML file |
| 16 | Cover embedding — adds `cover.xhtml` and updates OPF to declare the cover image |
| 17 | Final EPUB packaging |

## Basic invocation

```bash
python docx_to_kindle_epub.py \
  --input manuscript.docx \
  --cover ebook_cover.jpg \
  --output mybook.epub \
  --title "Your Book Title" \
  --subtitle "Your Subtitle" \
  --author "Author Name" \
  --isbn "978-X-XXXXXXX-X-X" \
  --publisher "Your Imprint"
```

## Customization flags

The pipeline handles most manuscripts without configuration. Two flags exist for book-specific patterns:

### `--dedication-first-line`

Books often have a dedication that should sit on its own page after the copyright. Pandoc doesn't always force a page break there. Supply the *exact* first words of your dedication and the pipeline will insert a clean page break before it.

```bash
--dedication-first-line "For my mother"
--dedication-first-line "To everyone who asked the question"
```

If your dedication is short (just a phrase), use the whole phrase. If it's a poem, use the first line.

### `--back-matter-marker` (repeatable)

If your back matter has bold-text section headers that should each start a fresh page (Glossary, Acknowledgments, Lineage notes, Bibliography), supply each marker as a separate flag:

```bash
--back-matter-marker "Glossary" \
--back-matter-marker "Acknowledgments" \
--back-matter-marker "Bibliography" \
--back-matter-marker "About the Author"
```

The pipeline finds each bold paragraph matching the exact text, promotes it to an `<h2>` with `page-break-before`, and styles it as a back-matter section heading.

### `--subtitle2`

Optional second subtitle line for the title page (e.g., a series tagline below the main subtitle).

```bash
--subtitle "The Main Subtitle"
--subtitle2 "Volume 1 of the Lineage Series"
```

## Output structure

The resulting `.epub` file contains:

```
mybook.epub  (zip file)
├── mimetype
├── META-INF/
│   └── container.xml
└── EPUB/
    ├── content.opf
    ├── nav.xhtml
    ├── toc.ncx
    ├── cover.xhtml
    ├── styles/kindle.css
    ├── images/cover.jpg
    ├── media/[chapter illustrations]
    └── text/
        ├── title_page.xhtml
        ├── ch001_*.xhtml
        ├── ch002_*.xhtml
        ...
        └── ch0NN_*.xhtml
```

KDP accepts this format directly. Upload via Kindle Direct Publishing → Bookshelf → Create Kindle eBook → Upload manuscript.

## Visual review with `epub_reviewer.py`

Before uploading, generate a browsable HTML preview to catch layout issues:

```bash
python epub_reviewer.py mybook.epub --output review/
# Open review/index.html in your browser
```

The reviewer shows every spine entry as a separate HTML page exactly as it'll render in Kindle (with the Kindle CSS applied), plus an index of issues found (orphaned tags, missing images, broken refs).

## Common gotchas

- **Pandoc is required**. The pipeline shells out to `pandoc`. Install via your system package manager.
- **Chapter detection is regex-based**. If your chapter markers aren't standard (`Chapter 1`, `PROLOGUE`, etc.), edit the `chapter_patterns` list in `detect_and_promote_headings()`.
- **Smart quotes are applied AFTER heading detection**. This is intentional — it lets `AUTHOR'S NOTE` match with either straight or curly apostrophes.
- **The cover image must be a JPG**, not PNG. KDP rejects PNG covers for Kindle ebooks (paperback covers are different — those use PDF).
- **If KDP rejects your EPUB with "broken TOC link"**, you almost certainly have anchor links that don't resolve across the split chapter files. The pipeline's `fix_cross_file_anchors()` step handles this — but only if you run the latest version with the cross-file fix.
