# Print pipeline — paperback / hardcover production

Eleven scripts that take a master `.docx` and produce a KDP-ready interior PDF + cover wrap PDF.

## Stage-by-stage

### Stage 3 — Reflow to trim

`reflow_to_trim.py` takes a master manuscript (typically US Letter at Georgia 11pt) and reflows it into trade trim format (5.5 × 8.5″ with serif body at the right size). Adjust the body font, line height, and margins for your book.

```bash
python scripts/book-publishing/reflow_to_trim.py \
  --input master.docx \
  --output trade_trim.docx \
  --trim 5.5x8.5 \
  --font "EB Garamond" \
  --body-size 11pt \
  --line-height 1.3
```

### Stage 3b — Tighten density

`tighten_density.py` adjusts word density per page toward a target benchmark (typical: 280-320 words/page for trade nonfiction). Keeps page count predictable, stabilizes the spine width.

```bash
python scripts/book-publishing/tighten_density.py \
  --input trade_trim.docx \
  --output trade_trim_tight.docx \
  --target-wpp 300
```

### Stage 4 — Footprint

`add_footprint.py` adds running headers (verso = book title, recto = chapter title), page numbers, and mirror margins (recto gets larger inside margin, verso gets larger outside).

```bash
python scripts/book-publishing/add_footprint.py \
  --input trade_trim_tight.docx \
  --output footprinted.docx \
  --book-title "Your Book Title"
```

### Stage 5 — CX audit + fixes

`audit_cx.py` reads the trade-trim PDF and flags customer-experience issues: widows (last line of paragraph alone on next page), orphans (first line of paragraph alone at bottom), headings followed by orphaned text, chapter-end widows.

```bash
# Convert docx to PDF first (libreoffice or Word)
libreoffice --headless --convert-to pdf footprinted.docx

# Run audit
python scripts/book-publishing/audit_cx.py footprinted.pdf
```

The audit output lists each issue with paragraph index. Pass those to `fix_orphans.py`:

```bash
python scripts/book-publishing/fix_orphans.py \
  footprinted.docx fixed.docx \
  --heading-orphans 12,47,89 \
  --global-widow
```

### Stage 5b — Pre-press polish

`pre_press_fix.py` applies final remediation: en-dash / em-dash normalization, double-space cleanup, smart-quote consistency, embedded-font verification, PDF metadata fixes.

```bash
python scripts/book-publishing/pre_press_fix.py \
  fixed.docx final.docx \
  --book-title "Your Book Title" \
  --author "Author Name" \
  --subject "Your Book Subject Line"
```

### Stage 6 — Cover wrap assembly

`assemble_cover_wrap.py` combines front cover + spine + back cover into a single wrap PDF at exact KDP dimensions.

First, calculate spine width from your page count:

```bash
python scripts/kdp-publishing/recalc_spine.py 250
# Output: Spine width for 250 pages on bw_white paper: 0.5625"
```

Then assemble:

```bash
python scripts/book-publishing/assemble_cover_wrap.py \
  --front front.png \
  --back back.png \
  --spine-image spine.png \
  --spine-width 0.5625 \
  --output cover_wrap.pdf
```

If you don't have a spine image, the script can generate one programmatically from text. See `--title`, `--subtitle`, `--author`, `--publisher` flags.

### Generate back cover (optional)

If you don't want to design the back cover in Photoshop / Canva, `generate_back_cover.py` produces one from a JSON config (hook, blurb paragraphs, pull quotes, bullets, author bio, barcode position, BISAC, price, imprint):

```bash
python scripts/book-publishing/generate_back_cover.py \
  --config examples/back-cover-config.json \
  --output back_generated.png
```

See `examples/back-cover-config.json` for the full schema.

### Stage 7 — Final verification

`verify_print_ready.py` runs final checks before upload: page count vs spine width, font embedding, no security restrictions, image resolution, file size under 650 MB.

```bash
python scripts/book-publishing/verify_print_ready.py \
  final.pdf \
  --trim 5.5x8.5 \
  --target-font "EB Garamond"
```

## Then run the KDP validators

See `docs/kdp-validators.md`. The validators replicate KDP's own checks locally so you catch issues before uploading.

## Upload to KDP

```
KDP → Bookshelf → Create Paperback
  → upload final.pdf (interior)
  → upload cover_wrap.pdf (cover)
  → review with KDP's previewer
  → publish
```

KDP reviews within 24-72 hours. If it accepts, order a $5 print proof. If the proof looks good, hit publish. If not, fix and re-upload.
