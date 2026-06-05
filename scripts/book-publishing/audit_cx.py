"""
Stage 5 — Programmatic CX issue detection on a print-ready PDF.

Flags:
- Severe widows (<100 chars body content on a non-display page)
- Sparse pages (100–300 chars on a body page)
- Heading orphans (last line is title-cased / no terminal punctuation)
- Placeholder text ([to be assigned], [forthcoming], TBD, etc.)
- Mid-sentence cuts (page ends with ', but' / ', and' / etc.)

False positives are EXPECTED — visually verify each flag before fixing.

Display pages (intentionally sparse) should be passed via --display-pages.
"""

import argparse
import re
import pdfplumber


def audit(pdf_path, display_pages=None, header_text="Y A T U"):
    if display_pages is None:
        display_pages = set()
    else:
        display_pages = set(display_pages)

    issues = {
        'severe_widow': [],
        'sparse': [],
        'heading_orphan': [],
        'placeholder': [],
        'mid_sentence_cut': [],
        'blank_unexpected': [],
    }

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            # Strip running header
            body = text.replace(header_text, "")
            # Strip standalone page numbers
            body = re.sub(r'^\s*\d{1,3}\s*$', '', body, flags=re.MULTILINE).strip()
            body = '\n'.join(line for line in body.split('\n') if line.strip())

            if not body:
                if i not in display_pages:
                    issues['blank_unexpected'].append((i, 0, '<BLANK>'))
                continue

            c = len(body.replace('\n', '').strip())
            first_line = body.split('\n')[0] if body else ""
            last_line = body.split('\n')[-1] if body else ""

            # Heading orphan: last line is short, mostly title-case, no terminal punctuation
            if last_line and 5 < len(last_line) < 60:
                words = last_line.split()
                if len(words) >= 2:
                    cap_ratio = sum(1 for w in words if w[0].isupper()) / len(words)
                    terminal = last_line[-1] in '.,!?:;"\u201D)\u2014\u2013'
                    if cap_ratio >= 0.6 and not terminal:
                        issues['heading_orphan'].append((i, last_line))

            # Severe widow
            if c < 100 and i not in display_pages:
                issues['severe_widow'].append((i, c, body[:120]))

            # Sparse page
            elif i not in display_pages and 100 <= c < 300:
                issues['sparse'].append((i, c, body[:80]))

            # Placeholder text
            for ph in ["[to be assigned]", "[forthcoming]", "TBD", "TODO", "[city]", "[N] years",
                       "[profession]", "[NAME]", "lorem ipsum"]:
                if ph in body.lower() or ph in body:
                    issues['placeholder'].append((i, ph))
                    break

            # Mid-sentence cut: ends with " but" / " and" / lowercase + no punctuation
            if last_line.lower().endswith((' but', ' and', ' or', ' so', ' the', ' a', ' an')):
                issues['mid_sentence_cut'].append((i, last_line[-40:]))

    return issues


def print_report(issues):
    total = sum(len(v) for v in issues.values())
    print(f"=== CX AUDIT — {total} flags ===\n")

    for category, label in [
        ('severe_widow', '🔴 SEVERE WIDOWS (<100 chars)'),
        ('heading_orphan', '🔴 HEADING ORPHANS (heading at bottom of page)'),
        ('sparse', '🟡 SPARSE PAGES (100–300 chars)'),
        ('placeholder', '🟢 PLACEHOLDER TEXT (TODO before final print)'),
        ('mid_sentence_cut', '🟡 MID-SENTENCE CUTS'),
        ('blank_unexpected', '🔴 UNEXPECTED BLANK PAGES'),
    ]:
        items = issues[category]
        print(f"\n{label}: {len(items)} found")
        for item in items:
            if len(item) == 3:
                pn, c, snip = item
                print(f"  P{pn} ({c} chars): {snip!r}")
            else:
                pn, snip = item
                print(f"  P{pn}: {snip!r}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("pdf", help="Print-ready PDF to audit")
    p.add_argument("--display-pages", default="", help="Comma-separated page numbers that are intentionally sparse (title, dedication, part dividers, etc.)")
    p.add_argument("--header", default="Y A T U", help="Running header text to strip")
    args = p.parse_args()
    dp = [int(x.strip()) for x in args.display_pages.split(',') if x.strip()] if args.display_pages else []
    issues = audit(args.pdf, display_pages=dp, header_text=args.header)
    print_report(issues)
