# Pipeline overview

A self-published book ships to KDP as **three deliverables**:

1. **Interior PDF** — the manuscript laid out at trim size, with running headers, page numbers, embedded fonts, and no orphan/widow issues
2. **Cover wrap PDF** — front cover + spine + back cover composed as one image at the exact KDP-required wrap dimensions
3. **Kindle EPUB** — the same manuscript reflowed for Kindle devices, with proper navigation, smart quotes, and a structured TOC

This toolkit produces all three from a master `.docx` source, with validators at every stage to catch issues before KDP catches them.

## The three pipelines

```
                   ┌─────────────────────────┐
                   │  Master .docx manuscript │
                   └──────────┬──────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ PRINT        │    │ COVER        │    │ EBOOK        │
│ pipeline     │    │ pipeline     │    │ pipeline     │
│              │    │              │    │              │
│ reflow_to_   │    │ generate_    │    │ docx_to_     │
│   trim       │    │   back_cover │    │   kindle_    │
│ tighten_     │    │ assemble_    │    │   epub       │
│   density    │    │   cover_wrap │    │ epub_        │
│ add_         │    │              │    │   reviewer   │
│   footprint  │    │              │    │              │
│ audit_cx     │    │              │    │              │
│ fix_orphans  │    │              │    │              │
│ pre_press_   │    │              │    │              │
│   fix        │    │              │    │              │
│              │    │              │    │              │
│ verify_      │    │ validate_    │    │              │
│   print_     │    │   cover      │    │              │
│   ready      │    │              │    │              │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                    │
       ▼                   ▼                    ▼
   interior.pdf      cover_wrap.pdf      mybook.epub
       │                   │                    │
       └─────────┬─────────┴─────────┬──────────┘
                 │                   │
                 ▼                   ▼
        ┌────────────────┐  ┌────────────────┐
        │ validate_      │  │ Upload to KDP  │
        │   metadata     │  │ paperback +    │
        │ validate_      │  │ Kindle         │
        │   paperback    │  │                │
        └────────────────┘  └────────────────┘
```

## Which files do you need before starting?

| Asset | Required for | How to produce |
|---|---|---|
| **Master `.docx`** | All three pipelines | Write in Word or Google Docs (export to docx) |
| **Front cover image** | Cover pipeline | Designed in Photoshop/Illustrator/Canva, sized 5.5×8.5″ + 0.125″ bleed at 300 DPI |
| **Back cover image** | Cover pipeline | Same as front, OR generate from text using `generate_back_cover.py` |
| **Spine image** | Cover pipeline | Vertical strip designed to match spine width × 8.75″ at 300 DPI |
| **Kindle cover JPG** | EPUB pipeline | 1600 × 2560 pixels, JPG, ≤ 5 MB |
| **ISBN** | Metadata + interior + cover | Buy from Bowker (US) or your country's ISBN agency |
| **Barcode PNG** | Cover pipeline (optional) | Generate from ISBN at bowker.com or barcode.tec-it.com |

## Recommended order

The first time you publish, walk through the pipelines in this order:

**Week -3 to -2 (manuscript polish):**
1. Run `reflow_to_trim.py` to convert your master docx to the trade trim format
2. Run `tighten_density.py` to adjust word density per page
3. Run `add_footprint.py` to add running headers + page numbers
4. Run `audit_cx.py` to find widows/orphans
5. Run `fix_orphans.py` to address what the audit flagged
6. Run `pre_press_fix.py` for final polish

**Week -2 to -1 (cover production):**
7. Design front cover, back cover, spine — OR use `generate_back_cover.py` for the back
8. Run `recalc_spine.py` to confirm correct spine width for your final page count
9. Run `assemble_cover_wrap.py` to build the wrap PDF
10. Run `validate_cover.py` to confirm dimensions match KDP expected

**Week -1 (final validation):**
11. Run `validate_paperback.py` on the interior PDF
12. Run `validate_metadata.py` on your KDP metadata JSON
13. Run `verify_print_ready.py` as the final pre-upload check

**Week -1 (ebook):**
14. Run `docx_to_kindle_epub.py` to produce the EPUB
15. Run `epub_reviewer.py` for visual review
16. Upload both the print and Kindle versions to KDP

## Subsequent docs

- `print-pipeline.md` — stage-by-stage detail of the print production pipeline
- `ebook-pipeline.md` — what `docx_to_kindle_epub.py` does and how to customize it
- `kdp-validators.md` — when and how to run each validator
- `customization.md` — book-specific patterns and how to configure them
