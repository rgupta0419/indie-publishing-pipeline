# Example: full Kindle EPUB pipeline invocation

Suppose your book has:

- A dedication that begins **"For everyone who held the line"**
- Back-matter sections titled **Glossary**, **Acknowledgments**, **Bibliography**, and **About the Author**
- A second subtitle line indicating it's part of a series

Full command:

```bash
python scripts/book-publishing/docx_to_kindle_epub.py \
  --input manuscript.docx \
  --cover ebook_cover.jpg \
  --output mybook.epub \
  --title "Your Book Title" \
  --subtitle "Your Subtitle" \
  --subtitle2 "Volume 1 of the Lineage Series" \
  --author "Author Name" \
  --isbn "978-X-XXXXXXX-X-X" \
  --publisher "Your Imprint" \
  --dedication-first-line "For everyone who held the line" \
  --back-matter-marker "Glossary" \
  --back-matter-marker "Acknowledgments" \
  --back-matter-marker "Bibliography" \
  --back-matter-marker "About the Author"
```

The pipeline will:

1. Convert `manuscript.docx` to EPUB
2. Detect and promote chapter headings
3. Add a page break before the paragraph starting with "For everyone who held the line"
4. Promote each of the four back-matter sections to its own page
5. Split the monolithic chapter into individual chapter files
6. Rebuild `nav.xhtml` and `toc.ncx` with proper TOC entries
7. Embed the cover
8. Package as `mybook.epub`

Run `epub_reviewer.py` afterward to visually verify everything before uploading to KDP.

---

## Minimal invocation (no customization)

If your book has no special dedication or back-matter sections:

```bash
python scripts/book-publishing/docx_to_kindle_epub.py \
  --input manuscript.docx \
  --cover ebook_cover.jpg \
  --output mybook.epub \
  --title "Your Book Title" \
  --author "Author Name"
```

All other arguments are optional. The pipeline runs ~12 transformations using sensible defaults.

---

## When to add `--dedication-first-line`

The pipeline already detects standard front-matter headings (`DEDICATION`, `AUTHOR'S NOTE`, `INTRODUCTION`, etc.) and promotes them to H1 with page breaks. The `--dedication-first-line` flag is only needed when:

- Your dedication doesn't have a literal heading like "DEDICATION" preceding it (common — many books just have the dedication poem appear right after the copyright page)
- The first line of your dedication is distinctive enough that the pipeline can pattern-match it

If you're not sure whether your book needs this flag, build the EPUB without it first, run `epub_reviewer.py`, and check whether the dedication has its own page. If it's bunched with the copyright text, add the flag.

## When to add `--back-matter-marker`

Use this when you have **bold-text paragraph headings** in the back matter that should each start a new page. Common cases:

- Glossary entries appearing right after the closing chapter without a section break
- Acknowledgments running together with the bibliography
- Multiple sub-sections within "About the Author" that should each have their own page

If your back-matter section is already an H1 or H2 heading in the docx, the pipeline auto-detects it — no flag needed.

## Where to find existing chapter detection patterns

Open `scripts/book-publishing/docx_to_kindle_epub.py` and search for `chapter_patterns`. You'll see the default list:

```python
chapter_patterns = [
    (r'^CHAPTER\s+\d+\.?\s*$', 1),
    (r'^Chapter\s+\d+:?\s+[A-Z][\w\s]{2,80}$', 1),
    (r'^PROLOGUE\s*$', 1),
    (r'^EPILOGUE\s*$', 1),
    (r'^PART\s+(ONE|TWO|THREE|FOUR|FIVE|[IVX]+)\s*$', 1),
    ...
]
```

If your book uses different conventions (e.g., "Section 1", "Movement One", "Book the First"), add patterns to this list.
