"""
EPUB Reviewer — generates a browsable HTML preview for visually inspecting an EPUB.

Extracts every XHTML file from an EPUB, applies the embedded CSS, and produces
a single HTML index page with navigation between chapters + per-chapter renderings.

Usage:
    python epub_reviewer.py path/to/book.epub --output review/

Outputs:
    review/
      index.html         # Navigation page (chapter list, jump to each)
      chapters/          # Per-chapter rendered HTML files
        cover.html
        ch001_title.html
        ch002_prologue.html
        ...
      assets/            # CSS and images copied from EPUB
"""

import argparse
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from html import escape


# Wrapper template that adds reviewer chrome around each chapter page
PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>{title}</title>
<link rel="stylesheet" type="text/css" href="../assets/kindle.css"/>
<style>
body {{
    max-width: 700px;
    margin: 0 auto;
    padding: 60px 40px 100px;
    background: #fafaf7;
    font-family: "EB Garamond", "Bookerly", Georgia, serif;
}}
.reviewer-header {{
    position: fixed;
    top: 0; left: 0; right: 0;
    background: #1a1a1a;
    color: #fff;
    padding: 12px 20px;
    z-index: 1000;
    font-family: -apple-system, system-ui, sans-serif;
    font-size: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}
.reviewer-header a {{ color: #f0c87a; text-decoration: none; margin: 0 12px; }}
.reviewer-header a:hover {{ text-decoration: underline; }}
.reviewer-issues {{
    background: #fef5e7;
    border: 1px solid #f0c87a;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 0 0 24px;
    font-family: -apple-system, system-ui, sans-serif;
    font-size: 13px;
    color: #6b4f2a;
}}
.reviewer-issues h4 {{ margin: 0 0 6px; font-size: 14px; color: #6b4f2a; }}
.reviewer-issues ul {{ margin: 4px 0 0 18px; padding: 0; }}
</style>
</head>
<body>
<div class="reviewer-header">
  <a href="../index.html">← Index</a>
  {prev_link}{next_link}
  <span style="float: right;">Page {page_num} of {page_total}: <strong>{title}</strong></span>
</div>
{issues_block}
<div class="page-content">
{body}
</div>
</body>
</html>
"""


INDEX_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>EPUB Review: {epub_name}</title>
<style>
body {{
    font-family: -apple-system, system-ui, sans-serif;
    max-width: 900px;
    margin: 0 auto;
    padding: 40px 30px;
    background: #f8f8f5;
    color: #2c2c2c;
}}
h1 {{ font-size: 28px; margin-bottom: 6px; color: #1a1a1a; }}
.subhead {{ color: #777; margin-bottom: 32px; font-size: 14px; }}
.stats {{
    background: #1a1a1a;
    color: #fff;
    padding: 20px 24px;
    border-radius: 8px;
    margin-bottom: 32px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
}}
.stat {{ text-align: center; }}
.stat .value {{ font-size: 28px; font-weight: bold; color: #f0c87a; }}
.stat .label {{ font-size: 12px; color: #aaa; margin-top: 4px; }}
.issues-summary {{
    background: #fef5e7;
    border: 1px solid #f0c87a;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 28px;
}}
.issues-summary h2 {{ margin: 0 0 8px; font-size: 16px; color: #6b4f2a; }}
.chapter-list {{ list-style: none; padding: 0; }}
.chapter-list li {{
    background: #fff;
    border: 1px solid #e0e0d8;
    border-radius: 6px;
    margin-bottom: 8px;
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: all 0.15s;
}}
.chapter-list li:hover {{
    border-color: #d4af6c;
    background: #fefcf8;
}}
.chapter-list a {{
    color: #1a1a1a;
    text-decoration: none;
    flex: 1;
    font-weight: 500;
}}
.chapter-meta {{
    color: #888;
    font-size: 12px;
    margin-left: 16px;
}}
.chapter-issues {{
    color: #b85c00;
    font-size: 11px;
    margin-left: 12px;
    font-weight: bold;
}}
.no-issues {{ color: #4a8a4a; }}
</style>
</head>
<body>
<h1>📖 EPUB Review</h1>
<p class="subhead">{epub_name} · Click any page to inspect</p>

<div class="stats">
  <div class="stat"><div class="value">{n_pages}</div><div class="label">Pages</div></div>
  <div class="stat"><div class="value">{n_words}</div><div class="label">Total Words</div></div>
  <div class="stat"><div class="value">{n_images}</div><div class="label">Images</div></div>
  <div class="stat"><div class="value">{n_issues}</div><div class="label">Issues Flagged</div></div>
</div>

{issues_summary}

<h2>Chapters / Sections</h2>
<ul class="chapter-list">
{chapter_list}
</ul>

</body>
</html>
"""


def detect_page_issues(content):
    """Heuristic issue detection per page."""
    issues = []

    # Plain-text body only — strip tags
    text = re.sub(r'<[^>]+>', '', content)
    text = re.sub(r'\s+', ' ', text).strip()

    # Straight quotes that should be curly
    straight_double = content.count('"')
    straight_single = content.count(chr(39))
    smart_double = content.count('“') + content.count('”')
    smart_single = content.count('‘') + content.count('’')

    if straight_double > 0 and straight_double > smart_double * 0.05:
        issues.append(f"{straight_double} straight double-quotes (should be curly)")
    if straight_single > 0 and straight_single > smart_single * 0.05:
        issues.append(f"{straight_single} straight single-quotes (should be curly)")

    # Look for "Chapter N" in plain text (means heading not promoted)
    chapter_in_text = len(re.findall(r'\bChapter\s+\d+\b', text))
    h1_count = len(re.findall(r'<h1[\s>]', content))
    if chapter_in_text > 1 and h1_count <= 1:
        issues.append(f"'{chapter_in_text}' Chapter X mentions, but only {h1_count} H1 — chapters not split")

    # Look for literal dash separators
    if '———' in content or '* * *' in content:
        issues.append("Section break uses literal dashes/asterisks (should be styled)")

    # MsoNormal artifacts
    if 'MsoNormal' in content or 'class="Mso' in content:
        issues.append("MS Word style artifacts present (MsoNormal)")

    # Empty paragraphs
    empty_p = len(re.findall(r'<p[^>]*>\s*</p>', content))
    if empty_p > 3:
        issues.append(f"{empty_p} empty paragraphs")

    # Tables without callout styling
    tables = re.findall(r'<table[^>]*>(.*?)</table>', content, re.DOTALL)
    plain_tables = sum(1 for t in tables if 'YOUR MOVE' in t.upper() or 'DEEP DIVE' in t.upper())
    callout_count = content.count('class="callout"')
    if plain_tables > callout_count:
        issues.append(f"{plain_tables} callout boxes still as plain tables")

    return issues


def extract_body(content):
    """Extract <body>...</body> inner content."""
    m = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
    if m:
        return m.group(1)
    return content


def count_words(text):
    """Strip tags and count words."""
    plain = re.sub(r'<[^>]+>', ' ', text)
    plain = re.sub(r'\s+', ' ', plain)
    return len(plain.split())


def main():
    p = argparse.ArgumentParser(description="Generate browsable HTML preview of an EPUB")
    p.add_argument("epub", help="Path to .epub file")
    p.add_argument("--output", default="epub_review", help="Output directory")
    args = p.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = output_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    print(f"Extracting EPUB: {args.epub}")
    print(f"Output: {output_dir}\n")

    temp_extract = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(args.epub, 'r') as zf:
            zf.extractall(temp_extract)

        # Find content root
        opf_files = []
        for root, _, files in os.walk(temp_extract):
            for fname in files:
                if fname.endswith('.opf'):
                    opf_files.append(os.path.join(root, fname))
        if not opf_files:
            print("No OPF found")
            sys.exit(1)
        content_root = os.path.dirname(opf_files[0])

        # Copy assets (CSS + images)
        for root, _, files in os.walk(content_root):
            for fname in files:
                if fname.endswith(('.css', '.jpg', '.jpeg', '.png', '.gif')):
                    src = os.path.join(root, fname)
                    dest = assets_dir / fname
                    shutil.copy2(src, dest)

        # Find all XHTML files in reading order from OPF spine
        with open(opf_files[0], 'r', encoding='utf-8') as f:
            opf_content = f.read()

        # Get spine order
        spine_refs = re.findall(r'<itemref\s+idref="([^"]+)"', opf_content)
        # Map ids to hrefs
        items = dict(re.findall(r'<item\s+id="([^"]+)"\s+href="([^"]+)"', opf_content))

        ordered_files = []
        for ref in spine_refs:
            if ref in items:
                href = items[ref]
                fpath = os.path.join(content_root, href)
                if os.path.exists(fpath) and fpath.endswith(('.xhtml', '.html')):
                    ordered_files.append(fpath)

        # Fallback if spine empty
        if not ordered_files:
            for root, _, files in os.walk(content_root):
                for fname in sorted(files):
                    if fname.endswith(('.xhtml', '.html')):
                        ordered_files.append(os.path.join(root, fname))

        print(f"Found {len(ordered_files)} XHTML pages in spine order\n")

        # Process each page
        pages = []
        total_words = 0
        total_images = 0
        total_issues = 0

        for i, fpath in enumerate(ordered_files):
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract title
            title_match = re.search(r'<title>([^<]+)</title>', content)
            title = title_match.group(1).strip() if title_match else os.path.basename(fpath)
            if not title or title == 'Untitled':
                # Try first h1
                h1m = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
                if h1m:
                    title = h1m.group(1).strip()
                else:
                    title = os.path.basename(fpath).replace('.xhtml', '')

            # Count
            body = extract_body(content)
            words = count_words(body)
            images = len(re.findall(r'<img\s', body))

            # Detect issues
            issues = detect_page_issues(content)

            total_words += words
            total_images += images
            total_issues += len(issues)

            # Adjust image src to point to assets dir
            body = re.sub(r'src="[^"]*/([^/"]+\.(jpg|jpeg|png|gif))"', r'src="../assets/\1"', body)
            body = re.sub(r'src="([^/"]+\.(jpg|jpeg|png|gif))"', r'src="../assets/\1"', body)

            pages.append({
                'index': i + 1,
                'title': title,
                'file': fpath,
                'body': body,
                'words': words,
                'images': images,
                'issues': issues,
            })

        # Generate per-chapter HTML pages
        for i, page in enumerate(pages):
            page_num = i + 1
            prev_link = f'<a href="page_{i:03d}.html">← Prev</a>' if i > 0 else ''
            next_link = f'<a href="page_{i+2:03d}.html">Next →</a>' if i < len(pages) - 1 else ''

            issues_block = ''
            if page['issues']:
                issues_html = '\n'.join(f'<li>{escape(iss)}</li>' for iss in page['issues'])
                issues_block = f'''<div class="reviewer-issues">
<h4>⚠ Issues detected on this page:</h4>
<ul>{issues_html}</ul>
</div>'''

            html = PAGE_TEMPLATE.format(
                title=escape(page['title']),
                prev_link=prev_link,
                next_link=next_link,
                page_num=page_num,
                page_total=len(pages),
                issues_block=issues_block,
                body=page['body'],
            )

            with open(chapters_dir / f"page_{page_num:03d}.html", 'w', encoding='utf-8') as f:
                f.write(html)

        # Generate index
        chapter_lis = []
        for page in pages:
            issue_str = ''
            if page['issues']:
                issue_str = f'<span class="chapter-issues">⚠ {len(page["issues"])} issue{"s" if len(page["issues"]) != 1 else ""}</span>'
            else:
                issue_str = '<span class="chapter-issues no-issues">✓ Clean</span>'

            chapter_lis.append(f'''<li>
<a href="chapters/page_{page['index']:03d}.html">📄 {escape(page['title'])}</a>
<span class="chapter-meta">{page['words']:,} words · {page['images']} images</span>
{issue_str}
</li>''')

        # Issues summary
        if total_issues > 0:
            issue_types = {}
            for page in pages:
                for iss in page['issues']:
                    key = iss.split(':')[0] if ':' in iss else iss.split('(')[0].strip()
                    issue_types[key] = issue_types.get(key, 0) + 1
            issues_html = '<ul>' + ''.join(f'<li>{escape(k)}: {v} occurrence{"s" if v != 1 else ""}</li>' for k, v in issue_types.items()) + '</ul>'
            issues_summary = f'''<div class="issues-summary">
<h2>⚠ {total_issues} issue{'s' if total_issues != 1 else ''} flagged across pages</h2>
{issues_html}
</div>'''
        else:
            issues_summary = '<div class="issues-summary" style="background: #e7f5e7; border-color: #4a8a4a; color: #2c5c2c;"><h2>✓ All pages clean</h2></div>'

        index_html = INDEX_TEMPLATE.format(
            epub_name=escape(os.path.basename(args.epub)),
            n_pages=len(pages),
            n_words=f'{total_words:,}',
            n_images=total_images,
            n_issues=total_issues,
            issues_summary=issues_summary,
            chapter_list='\n'.join(chapter_lis),
        )

        with open(output_dir / "index.html", 'w', encoding='utf-8') as f:
            f.write(index_html)

        print(f"=== Review Generated ===")
        print(f"Pages:         {len(pages)}")
        print(f"Total words:   {total_words:,}")
        print(f"Total images:  {total_images}")
        print(f"Issues found:  {total_issues}")
        print(f"\nOpen in browser: {output_dir}/index.html")

    finally:
        shutil.rmtree(temp_extract)


if __name__ == "__main__":
    main()
