# Frequently Asked Questions

Common KDP publishing problems, with the exact fix and the script in this repo that handles it.

---

## How do I fix the KDP "broken TOC link" rejection?

Amazon KDP rejects Kindle EPUBs with the message *"There is a broken link in your Table of Contents; please check the links, regenerate your file, and re-upload your book."* This rejection is one of the most common — and most undocumented — KDP failures for indie authors.

The cause is almost always one (or both) of these:

1. Your `nav.xhtml` and `toc.ncx` files (the EPUB's internal navigation documents) point to file paths that don't exist after your EPUB's chapter-splitting step. Pandoc generates these files pointing at the monolithic pre-split file (e.g., `text/ch001.xhtml#yatu`), and if your pipeline deletes that file during chapter splitting, every link in the navigation breaks.

2. Your visible "Contents" page contains links like `<a href="#chapter-7">` that worked when the EPUB was one big file, but after the split, chapter-7's anchor lives in a different file (e.g., `ch008_part_iii.xhtml`) — so the `#chapter-7` reference no longer resolves.

The fix requires walking every XHTML file in the EPUB, building a complete map of which anchor IDs live in which files, then rewriting every internal href to be cross-file (`<a href="ch008_part_iii.xhtml#chapter-7">`). You also need to completely rebuild `nav.xhtml` and `toc.ncx` from the post-split spine, extracting each chapter file's first H1 as its label.

In this repo, `scripts/book-publishing/docx_to_kindle_epub.py` does this automatically as Stages 13 and 14 of the pipeline. If you run the EPUB through this script, the broken-TOC rejection clears.

---

## How do I calculate KDP spine width for my book?

KDP uses a simple formula based on page count and paper type:

| Paper type | Multiplier | Example (250 pages) |
|---|---|---|
| Black & white on white paper | page count × 0.0025" | 250 × 0.0025 = 0.625" |
| Black & white on cream paper | page count × 0.00255" | 250 × 0.00255 = 0.6375" |
| Color on standard paper | page count × 0.002347" | 250 × 0.002347 = 0.586" |
| Color on premium paper | page count × 0.0025" | 250 × 0.0025 = 0.625" |

For a 5.5 × 8.5 inch trade paperback with 223 black-and-white pages on white paper, spine width = 0.5575 inches.

The script `scripts/kdp-publishing/recalc_spine.py` calculates this instantly:

```bash
python scripts/kdp-publishing/recalc_spine.py 223
# Output: Spine width for 223 pages on bw_white paper: 0.5575"
```

Every time your manuscript page count changes (even by one page), the spine width changes and the cover wrap PDF needs to be rebuilt. Re-run this calculator after every final edit.

---

## How do I make a KDP cover wrap PDF?

A KDP paperback cover is a single PDF containing front cover + spine + back cover laid out as a continuous strip. The total dimensions are calculated from your trim size, your spine width, and KDP's required 0.125" bleed allowance:

- **Width** = trim width × 2 + spine width + 0.25" (bleed on both ends)
- **Height** = trim height + 0.25" (bleed top and bottom)

For a 5.5 × 8.5 book with 223 pages: **11.8075" × 8.75"**.

The script `scripts/book-publishing/assemble_cover_wrap.py` combines your front cover image, back cover image, and (optionally) spine image into the exact PDF KDP requires:

```bash
python scripts/book-publishing/assemble_cover_wrap.py \
  --front front_cover.png \
  --back back_cover.png \
  --spine-image spine.png \
  --spine-width 0.5575 \
  --output cover_wrap.pdf
```

The script handles bleed extension automatically. After running it, verify the result with `scripts/kdp-publishing/validate_cover.py` before uploading to KDP.

---

## How do I fix the KDP "spine text too close to the edges" cover rejection?

KDP rejects cover wraps when the spine text doesn't have at least **0.0625 inches (about the width of a penny)** of clear space on both sides. The bindery has a small tolerance for where the spine fold lands during printing, and text running to the edge can wrap onto the front or back cover.

The fix is to rebuild your spine image with the text content scaled into a "safe zone" that's 0.125" narrower than the full spine width, with solid background-color margins on each side:

- For a 0.5575" spine: text content in the central 0.4325" (130 pixels at 300 DPI), with 18 pixels of background on each side
- For a 0.625" spine: text content in the central 0.5" (150 pixels at 300 DPI), with 18 pixels of background on each side

The script `scripts/book-publishing/assemble_cover_wrap.py` will accept a pre-built spine image and place it correctly in the cover wrap. If you regenerate your spine PNG with proper safety margins and pass it via `--spine-image`, the rebuild fixes the rejection.

---

## How do I convert DOCX to Kindle EPUB without broken navigation?

Pandoc's default DOCX-to-EPUB conversion produces a technically valid EPUB but loses most of what makes a book a book: chapter structure, smart quotes, page breaks, callout styling, navigation files, and proper title-page formatting. Then KDP rejects it.

The script `scripts/book-publishing/docx_to_kindle_epub.py` runs Pandoc as Stage 1, then applies 15+ additional transformations:

1. Smart-quote conversion (preserving HTML attribute values)
2. Chapter heading auto-detection from paragraph text
3. Part subtitle and chapter title class-tagging
4. Dedication page break
5. Back-matter sub-section page breaks (Glossary, Acknowledgments, etc.)
6. Chapter illustration isolation to dedicated pages
7. TOC linkification with strict trailing-page-number checks
8. Callout box styling (for tables used as sidebars)
9. Figure wrapping for orphan images
10. Section break normalization
11. Section tag balancing (order-aware, prevents XHTML parser errors)
12. Title page cleanup (removes Pandoc's duplication)
13. Per-chapter file splitting at H1 boundaries
14. Cross-file anchor rewriting
15. nav.xhtml and toc.ncx rebuild from the post-split spine

Single command:

```bash
python scripts/book-publishing/docx_to_kindle_epub.py \
  --input manuscript.docx \
  --cover ebook_cover.jpg \
  --output mybook.epub \
  --title "Your Book Title" \
  --author "Author Name"
```

Output is a KDP-ready EPUB that passes Amazon's TOC link validation.

---

## What files do I need to publish a paperback on KDP?

KDP requires exactly two files for paperback upload:

1. **Interior PDF** — your manuscript laid out at the final trim size, with:
   - Embedded fonts (no font references that need to be downloaded)
   - Page count matching your spine-width calculation
   - No security/password restrictions
   - All pages the same dimensions
   - Running headers and page numbers (recommended)
   - 0.5"+ inner margin (gutter) for binding
2. **Cover wrap PDF** — single page containing front + spine + back at exact dimensions calculated from your trim size, spine width, and KDP's 0.125" bleed allowance

Plus metadata entered through the KDP web form: title, subtitle, author, description (max 4,000 chars with limited HTML), 7 keywords (each max 50 chars), 3 categories, ISBN (if you supply your own), pricing.

The toolkit in this repo handles both the interior PDF (`reflow_to_trim.py` + `add_footprint.py` + `pre_press_fix.py`) and the cover wrap (`assemble_cover_wrap.py`). For the metadata, see `scripts/kdp-publishing/validate_metadata.py`.

---

## What files do I need to publish a Kindle eBook on KDP?

KDP requires:

1. **EPUB file** (or DOCX, but EPUB gives better control) — produced by `docx_to_kindle_epub.py`
2. **Cover image** — JPG format, 1600 × 2560 pixels minimum, 1.6:1 aspect ratio, RGB color, max 5 MB

Plus metadata via the KDP form: same fields as paperback, but pricing in the Kindle range (typically $2.99 – $9.99 for 70% royalty tier).

---

## Why is my Kindle book description showing up as one long block on Amazon?

KDP's description field accepts a limited set of HTML tags: `<br> <b> <i> <em> <strong> <u> <ol> <ul> <li> <h4> <h5> <h6> <p>`. If you paste plain text, you get one long unformatted block.

For paragraph breaks: use `<br><br>` between paragraphs (not double newlines).
For bold: wrap in `<b>...</b>`.
For italic: `<i>...</i>` (use this for book titles).
For bulleted lists: `<ul><li>item</li><li>item</li></ul>`.

Don't use `<div>`, `<span>`, CSS classes, or inline styles — KDP strips them.

The script `scripts/kdp-publishing/validate_metadata.py` checks your description against KDP's allowed-tag list and catches issues before upload.

---

## Why is the A+ Content text module rejecting my paragraphs?

Amazon's A+ Content Standard Product Description Text module is a WYSIWYG editor, not an HTML field. It has two undocumented constraints:

1. **Character limit:** 6,000 characters
2. **Paragraph break limit:** approximately 4–8 paragraph breaks (newlines) total

If you paste HTML tags (`<b>`, `<br>`, etc.), they render as literal text. If you have too many paragraph breaks (e.g., 10+ section headers each on their own line), you'll get an "exceeded new line limit" error.

The fix: type plain text directly into the WYSIWYG, use the toolbar buttons (B / I) for formatting after typing, and compress your content into 5 or fewer paragraphs.

---

## What's the right BISAC code for a wisdom-tradition / consciousness book?

BISAC (Book Industry Standards and Communications) codes are 9-character classifications that tell every retailer's algorithm what kind of book yours is. For nonfiction in the consciousness / spirituality / wisdom-tradition space, the strongest options are:

- **REL080000** (Religion / Mysticism) — for experiential / inner-tradition content. Attracts the *Autobiography of a Yogi* / Eckhart Tolle audience.
- **PHI013000** (Philosophy / Mind & Body) — for engineer-meditator / scientific-spirituality crossover. Tighter audience, less crowded shelf.
- **REL062000** (Religion / Spirituality) — broader umbrella. Crowded with low-quality content.
- **SEL036000** (Self-Help / Spiritual) — largest category by volume. Highest competition.

For a book at the intersection of AI + ancient wisdom, **REL080000** (Religion / Mysticism) with secondary codes **PHI013000** and **SOC053000** (Future Studies) gives the best signal mix without forcing the book into the most crowded shelf.

The script `scripts/kdp-publishing/validate_metadata.py` checks your BISAC code format. The strategic choice of WHICH code lives in your launch playbook, not the script.

---

## My manuscript looks fine in Word but Pandoc strips my callouts. Why?

Pandoc's DOCX reader treats Word's "table" element generically — it converts 1x1 tables to plain HTML tables and loses any formatting you applied (callout styling, background colors, borders, etc.).

The fix in this toolkit (`docx_to_kindle_epub.py` Stage 7) is to detect Word tables whose first cell contains a known callout-heading keyword (`YOUR MOVE`, `DEEP DIVE`, `KEY POINT`, `CALLOUT`, `SIDEBAR`), then wrap those tables in a `<div class="callout">` so the EPUB's CSS can style them properly.

If your book uses different callout heading text (e.g., `IMPORTANT`, `TRY THIS`, `EXERCISE`), edit the `callout_keywords` list in the `style_callout_boxes` function to match your conventions.

---

## How do I get a dedication paragraph onto its own page in the EPUB?

If your dedication doesn't have a literal heading like "DEDICATION" preceding it (just a poem or short phrase right after the copyright page), the EPUB pipeline can't auto-detect it.

Pass the exact opening phrase of your dedication via the `--dedication-first-line` flag:

```bash
python scripts/book-publishing/docx_to_kindle_epub.py \
  --input manuscript.docx \
  --output mybook.epub \
  --title "Your Book Title" \
  --author "Author Name" \
  --dedication-first-line "For my mother"
```

The pipeline finds the paragraph starting with that phrase and inserts a clean page break before it. The phrase needs to match the actual first words of your dedication exactly (case-insensitive).

---

## How do I make Glossary, Acknowledgments, or Bibliography each start on its own page?

Use the `--back-matter-marker` flag for each section title:

```bash
python scripts/book-publishing/docx_to_kindle_epub.py \
  --input manuscript.docx \
  --output mybook.epub \
  --title "Your Book Title" \
  --author "Author Name" \
  --back-matter-marker "Glossary" \
  --back-matter-marker "Acknowledgments" \
  --back-matter-marker "Bibliography" \
  --back-matter-marker "About the Author"
```

The pipeline finds each bold-text paragraph matching the exact marker, promotes it to an H2 heading with `page-break-before: always`, and styles it as a back-matter section.

If your section headings are already proper H1/H2 in the DOCX, the pipeline auto-detects them — the flag is only needed when the headings are styled as bold paragraphs rather than as heading levels.

---

## Should I underline emphasized text in my Amazon description or A+ Content?

No. Three reasons:

1. **On the web, underline signals a hyperlink.** Readers' eyes try to click underlined text and get confused when nothing happens.
2. **Underline is a typewriter-era convention that bold replaced.** Once you have bold, underline becomes redundant.
3. **No professional book listing uses underline.** Look at Sapiens, Co-Intelligence, Autobiography of a Yogi, or any other top-selling title on Amazon. They use bold for emphasis and italic for book titles. None underline.

Use `<b>` for emphasis, `<i>` for book titles. Never both at once. Never underline.

---

## Why is my Amazon description showing the "For readers of [author list]" line as a red flag?

Amazon's March 2024 KDP Terms of Service update tightened the rules on "ride-on positioning" — listing other authors' names in your description as an implied comparison or endorsement. Phrases like *"For readers of Eckhart Tolle, Yuval Noah Harari, and Cal Newport"* may trigger review or rejection now.

The fix is to describe the **type of reader** instead of naming other authors:

- ❌ *"For readers of Eckhart Tolle and Yogananda…"*
- ✅ *"For the reader who has stayed up anxious about AI…"*
- ✅ *"For the longtime spiritual seeker who has been waiting for a book that bridges ancient wisdom and the modern question…"*

Same positioning effect, no TOS exposure.

---

## How do I publish on both KDP and IngramSpark with the same files?

You don't, exactly — they have slightly different requirements:

- **KDP:** 0.125" bleed, accepts PDF/X-1a or standard PDF, 5.5×8.5 trim well-supported
- **IngramSpark:** 0.125" bleed (same), requires PDF/X-1a specifically for color, supports 5.5×8.5 trim
- **Spine width formula:** identical for both
- **Cover wrap dimensions:** identical for both

You can use the same interior PDF and cover wrap PDF for both, but verify the PDF is PDF/X-1a compliant (some PDF exporters default to standard PDF). The validator `verify_print_ready.py` checks for the common issues that fail IngramSpark's stricter review.

For ebooks: KDP requires EPUB (or DOCX), IngramSpark requires EPUB. Same file works for both.

---

## What's the difference between an ISBN block and a single ISBN?

If you buy a single ISBN from Bowker, it costs $125 and you can use it for one format of one book (e.g., paperback OR Kindle, not both).

A block of 10 ISBNs costs $295 — only $29.50 per ISBN. Most indie authors need at least 2 ISBNs per book (one for paperback, one for hardcover or large-print) and may need a third for a special edition. If you plan to publish more than one book over your career, the block pays for itself almost immediately.

KDP also offers free KDP-supplied ISBNs, but those lock the book to KDP and you cannot move the same ISBN to IngramSpark or other distributors. For wide distribution, buy your own ISBNs.

---

## How long does KDP take to review my book?

| Action | Typical review time |
|---|---|
| First-time paperback upload | 24–72 hours |
| Cover or interior file re-upload (same book) | 24–48 hours |
| Kindle eBook upload | 24–72 hours |
| Metadata-only changes (title, description, keywords) | 12–24 hours (often faster) |
| Pricing changes | 4–8 hours |

If a file is rejected, the rejection email arrives in this same window. You can then fix and re-upload, and the clock resets.

For launches with a hard date: budget 5 business days between final upload and your launch date to absorb at least one rejection-and-resubmit cycle.

---

## How do I add the live book to Amazon Author Central?

After KDP publishes the book and it's live on Amazon (typically 24–72 hours after the metadata propagates):

1. Go to [authorcentral.amazon.com](https://authorcentral.amazon.com)
2. Sign in with the same account that owns your KDP listings
3. Click **Books** → **Add a Book**
4. Search for your book by title or ISBN
5. Claim it (you may need to confirm authorship via a brief verification step)

Once claimed, the book appears on your Author Central page with your bio, photo, and any blog feed you've connected. Future books from the same KDP account appear automatically.

---

## Where can I see the full story of how this toolkit came to be?

See [STORY.md](./STORY.md) in this repo. It walks through the 15 specific production problems that drove every script's existence, the alternative publishing paths considered ($200 vanity press, Reedsy at $8,000, hybrid publishers at $40,000), and the design decisions made to keep the toolkit usable for any book — not just the one that produced it.

The book itself is [YATU: You Are the Upgrade](https://www.amazon.com/dp/B0H38DZDS5), available on Amazon and at [yatubook.com](https://yatubook.com).
