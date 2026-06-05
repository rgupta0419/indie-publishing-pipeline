# KDP validators

Four pre-flight scripts that replicate KDP's own validation logic locally. Run these BEFORE uploading to catch issues that would otherwise come back as KDP rejections (each rejection cycle costs 24–72 hours).

## `recalc_spine.py` — spine width calculator

Given a page count, returns the correct spine width per KDP's formula.

```bash
python scripts/kdp-publishing/recalc_spine.py 250
# Output: Spine width for 250 pages on bw_white paper: 0.5625"
```

Use this every time your manuscript page count changes. The cover wrap PDF needs to match the new spine width or KDP will reject it.

Options:
- `--paper bw_white` (default) — black & white interior on white paper
- `--paper bw_cream` — black & white interior on cream paper
- `--paper color_standard` — color interior on standard paper
- `--paper color_premium` — color interior on premium paper

## `validate_cover.py` — cover wrap pre-flight

Validates the assembled cover wrap PDF against KDP's expected dimensions.

```bash
python scripts/kdp-publishing/validate_cover.py \
  cover_wrap.pdf \
  --trim 5.5x8.5 \
  --pages 250
```

Checks:
- Single-page PDF (required)
- Width matches expected (trim_w * 2 + spine + 2 * bleed)
- Height matches expected (trim_h + 2 * bleed)
- File size under 650 MB
- Spine width matches page count

Output `=== STATUS: PASS ===` means safe to upload. Anything else needs fixing first.

## `validate_paperback.py` — interior PDF pre-flight

Validates the manuscript interior PDF against KDP's requirements.

```bash
python scripts/kdp-publishing/validate_paperback.py \
  interior.pdf \
  --trim 5.5x8.5
```

Checks:
- All pages match trim size (not US Letter, not A4)
- Fonts are embedded (no missing-font fallbacks)
- No password protection or security restrictions
- No oversized images (≤ 6 MP)
- Page count within KDP's 24-828 range
- No transparency issues
- PDF version compatible

## `validate_metadata.py` — KDP metadata pre-flight

Validates your KDP metadata JSON against KDP rules (title length, description HTML, keyword limits, BISAC format).

```bash
python scripts/kdp-publishing/validate_metadata.py metadata.json
```

Checks:
- Title ≤ 200 chars
- Subtitle ≤ 200 chars
- Description ≤ 4,000 chars
- Description HTML uses only allowed tags (`<br> <b> <i> <em> <strong> <ol> <ul> <li> <h4>-<h6> <p>`)
- No banned phrases in description (`#1 bestseller`, `free`, etc.)
- Keywords ≤ 50 chars each, ≤ 7 total
- Categories in expected format
- ISBN format valid (979-X-XXXXXXX-X-X)
- Price within KDP's allowed range
- Page count consistent with trim size

See `examples/metadata-example.json` for the expected schema.

## When to run each

| Stage | Run these |
|---|---|
| After every manuscript edit that changes page count | `recalc_spine.py` |
| After building or rebuilding the cover wrap | `validate_cover.py` |
| Before uploading the interior PDF | `validate_paperback.py` |
| Before pasting metadata into KDP forms | `validate_metadata.py` |
| All four, one last time | Final pre-upload checklist |
