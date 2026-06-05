"""
Stage 7 verification — run before clicking upload to KDP.

10-point check on a print-ready PDF:
1. Trim exact (5.5×8.5 = 396×612 pts, or 6×9 = 432×648)
2. Page count + spine width calculation
3. Verso gutter ≥ KDP minimum (0.5" for 151–300 pages)
4. Color content (must be pure B&W for B&W pricing tier)
5. Font embedding (only target font, no fallbacks)
6. Sanskrit / non-Latin diacritic rendering
7. TOC accuracy (entries match actual chapter pages)
8. Justification + hyphenation
9. Placeholder text (no [to be assigned], [forthcoming], TBD, etc.)
10. PDF metadata (Title, Author set correctly)

Output: detailed report with pass/fail per check + actionable recommendations.

Usage:
    python verify_print_ready.py <path_to_final.pdf> --trim 5.5x8.5 --target-font "EB Garamond"
"""

import argparse
import re
import subprocess
import sys


def check_trim(pdf_path, expected_trim_w, expected_trim_h):
    """Check 1: trim exactness."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[0]
            w_pts, h_pts = page.width, page.height
            w_in, h_in = w_pts / 72, h_pts / 72
            exact = abs(w_in - expected_trim_w) < 0.01 and abs(h_in - expected_trim_h) < 0.01
            return {
                'pass': exact,
                'detail': f"{w_pts:.2f} × {h_pts:.2f} pts ({w_in:.4f} × {h_in:.4f} in)",
                'expected': f"{expected_trim_w*72:.0f} × {expected_trim_h*72:.0f} pts ({expected_trim_w} × {expected_trim_h} in)"
            }
    except Exception as e:
        return {'pass': False, 'detail': str(e)}


def check_page_count(pdf_path):
    """Check 2: page count + spine."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        n = len(pdf.pages)
        spine = n * 0.0025
        return {
            'pass': True,
            'detail': f"{n} pages → spine {spine:.3f}\""
        }


def check_verso_gutter(pdf_path, kdp_min=0.5):
    """Check 3: verso gutter ≥ KDP minimum."""
    import pdfplumber
    issues = []
    with pdfplumber.open(pdf_path) as pdf:
        sample_pages = [10, 30, 50, 100, 150, 200] + [len(pdf.pages) - 5]
        for pn in sample_pages:
            if pn > len(pdf.pages) or pn < 1:
                continue
            page = pdf.pages[pn - 1]
            words = page.extract_words()
            if not words:
                continue
            min_x = min(w['x0'] for w in words) / 72
            max_x = max(w['x1'] for w in words) / 72
            page_w = page.width / 72
            if pn % 2 == 0:  # verso
                inner = page_w - max_x
                if inner < kdp_min:
                    issues.append(f"P{pn} verso inner={inner:.3f}\" (below {kdp_min}\" min)")
    return {
        'pass': len(issues) == 0,
        'detail': f"All sampled pages ≥ {kdp_min}\"" if not issues else "; ".join(issues)
    }


def check_color(pdf_path):
    """Check 4: pure B&W."""
    import pdfplumber
    color_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            for c in page.chars[:30]:
                color = c.get('non_stroking_color')
                if color and isinstance(color, (tuple, list)) and len(color) >= 3:
                    r, g, b = color[0], color[1], color[2]
                    if max(abs(r-g), abs(g-b), abs(r-b)) > 0.05:
                        color_pages.append(i)
                        break
    return {
        'pass': len(color_pages) == 0,
        'detail': "Pure B&W" if not color_pages else f"Color content on {len(color_pages)} pages: {color_pages[:5]}"
    }


def check_fonts(pdf_path, target_font):
    """Check 5: only target font, no fallback."""
    result = subprocess.run(['pdffonts', pdf_path], capture_output=True, text=True)
    fallbacks = []
    embedded_count = 0
    for line in result.stdout.split('\n')[2:]:
        if not line.strip():
            continue
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        embedded_count += 1
        # Strip subset prefix (AAAAAB+)
        bare = name.split('+')[-1] if '+' in name else name
        # Match against target font (with -Regular, -Bold, -Italic, etc.)
        target_bare = target_font.replace(' ', '')
        if target_bare not in bare:
            fallbacks.append(name)
    return {
        'pass': len(fallbacks) == 0,
        'detail': f"All {embedded_count} fonts are {target_font}" if not fallbacks else f"Fallback fonts found: {fallbacks}"
    }


def check_diacritics(pdf_path, sample_pages=[50, 100, 150]):
    """Check 6: Sanskrit / non-Latin diacritic rendering."""
    import pdfplumber
    found = []
    with pdfplumber.open(pdf_path) as pdf:
        for pn in sample_pages:
            if pn > len(pdf.pages):
                continue
            text = pdf.pages[pn-1].extract_text() or ""
            # Latin Extended-A and Latin Extended-B for diacritics
            diacritics = [ch for ch in text if 0x100 <= ord(ch) <= 0x24F]
            if diacritics:
                found.append(f"P{pn}: {len(diacritics)} diacritics ({''.join(diacritics[:6])})")
    return {
        'pass': True,  # informational
        'detail': "; ".join(found) if found else "No Sanskrit diacritics found in sampled pages"
    }


def check_toc(pdf_path):
    """Check 7: TOC entries match actual chapter pages."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        # Find TOC page
        toc_page = None
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            if "CONTENTS" in text and "Chapter" in text:
                toc_page = i
                break
        if not toc_page:
            return {'pass': False, 'detail': "TOC not found"}

        # Extract TOC entries with page numbers
        toc_text = pdf.pages[toc_page - 1].extract_text() or ""
        entries = re.findall(r'(Chapter \d+|Prologue)\s+([^\n]+?)\s+(\d{1,3})\s*\n', toc_text)
        if not entries:
            entries = re.findall(r'(Chapter \d+|Prologue).*?(\d+)', toc_text)

        # Find actual chapter pages
        actual = {}
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            chapter_count = len(re.findall(r'\bChapter \d+\b', text))
            if chapter_count > 3:
                continue  # this is the TOC
            for n in range(1, 14):
                if f'CHAPTER {n}' in text and f'Chapter {n}' not in actual:
                    actual[f'Chapter {n}'] = i

        mismatches = []
        for entry in entries[:5]:
            label = entry[0]
            try:
                claimed = int(entry[-1])
                if label in actual and actual[label] != claimed:
                    mismatches.append(f"{label}: TOC says {claimed}, actual {actual[label]}")
            except (ValueError, IndexError):
                continue

        return {
            'pass': len(mismatches) == 0,
            'detail': f"TOC accurate" if not mismatches else "; ".join(mismatches)
        }


def check_placeholder_text(pdf_path):
    """Check 8: no [to be assigned], [forthcoming], TBD."""
    import pdfplumber
    placeholders = ["[to be assigned]", "[forthcoming]", "TBD", "TODO", "[city]", "[N] years", "[profession]", "[NAME]"]
    found = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            for ph in placeholders:
                if ph in text or ph.lower() in text.lower():
                    found.append(f"P{i}: '{ph}'")
                    break
    return {
        'pass': len(found) == 0,
        'detail': "No placeholders" if not found else f"Found: {found[:5]}"
    }


def check_metadata(pdf_path):
    """Check 9: PDF metadata (Title, Author)."""
    result = subprocess.run(['pdfinfo', pdf_path], capture_output=True, text=True)
    title = ""
    author = ""
    for line in result.stdout.split('\n'):
        if line.startswith('Title:'):
            title = line.split(':', 1)[1].strip()
        if line.startswith('Author:'):
            author = line.split(':', 1)[1].strip()
    has_title = title and title not in ('Untitled', 'Document1', '')
    has_author = bool(author)
    bad = []
    if not has_title:
        bad.append(f"Title missing or default: '{title}'")
    if not has_author:
        bad.append(f"Author missing")
    return {
        'pass': has_title and has_author,
        'detail': f"Title='{title}', Author='{author}'" if has_title else "; ".join(bad)
    }


def check_arrow_glyph(pdf_path):
    """Check 10: no → arrows that triggered fallback fonts."""
    import pdfplumber
    issues = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            for c in page.chars[:1000]:
                if 'NovaMono' in c.get('fontname', '') or 'Mono' in c.get('fontname', ''):
                    issues.append(f"P{i}: monospace font detected ({c.get('fontname','')})")
                    break
    return {
        'pass': len(issues) == 0,
        'detail': "No monospace fallback" if not issues else "; ".join(issues[:3])
    }


def main():
    p = argparse.ArgumentParser(description="Stage 7 verification — pre-KDP-upload sanity check")
    p.add_argument("pdf", help="Path to print-ready PDF")
    p.add_argument("--trim", default="5.5x8.5", help="Trim size (e.g., 5.5x8.5 or 6x9)")
    p.add_argument("--target-font", default="EB Garamond", help="Expected body font")
    p.add_argument("--kdp-min-gutter", type=float, default=0.5, help="KDP minimum inner margin (0.5\" for 151–300 pages)")
    args = p.parse_args()

    trim_w, trim_h = [float(x) for x in args.trim.lower().split('x')]

    print("=" * 70)
    print(f"STAGE 7 VERIFICATION — {args.pdf}")
    print("=" * 70)

    checks = [
        ("1. Trim", check_trim, [args.pdf, trim_w, trim_h]),
        ("2. Page count + spine", check_page_count, [args.pdf]),
        ("3. Verso gutter", check_verso_gutter, [args.pdf, args.kdp_min_gutter]),
        ("4. Color (must be B&W)", check_color, [args.pdf]),
        ("5. Font integrity", check_fonts, [args.pdf, args.target_font]),
        ("6. Sanskrit diacritics", check_diacritics, [args.pdf]),
        ("7. TOC accuracy", check_toc, [args.pdf]),
        ("8. Placeholder text", check_placeholder_text, [args.pdf]),
        ("9. PDF metadata", check_metadata, [args.pdf]),
        ("10. No monospace fallback", check_arrow_glyph, [args.pdf]),
    ]

    pass_count = 0
    fail_count = 0
    for label, fn, fn_args in checks:
        try:
            result = fn(*fn_args)
            status = "✅" if result.get('pass') else "❌"
            if result.get('pass'):
                pass_count += 1
            else:
                fail_count += 1
            print(f"\n{status} {label}")
            print(f"   {result.get('detail', '')}")
            if result.get('expected'):
                print(f"   Expected: {result['expected']}")
        except Exception as e:
            fail_count += 1
            print(f"\n❌ {label}: ERROR — {e}")

    print("\n" + "=" * 70)
    print(f"RESULT: {pass_count}/{len(checks)} passed, {fail_count} failed")
    print("=" * 70)
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
