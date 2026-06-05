"""
Convert a docx manuscript to a Kindle-ready EPUB with smart formatting fixes.

Pipeline:
1. Pandoc converts docx → EPUB 3 base
2. Heading auto-detection — finds chapter markers ("Chapter 1", "PROLOGUE", etc.)
   in paragraphs and promotes them to <h1>/<h2>
3. Chapter splitting — splits monolithic ch001.xhtml into per-chapter files
4. Smart-quote conversion — replaces straight quotes with curly quotes
5. Callout-box styling — wraps tables (YOUR MOVE / DEEP DIVE) with proper CSS class
6. Figure wrapping — wraps images in <figure> tags for proper rendering
7. Title-page cleanup — removes duplicate title fragments
8. Section break normalization — converts "———" to proper centered separators
9. Inject Kindle-optimized CSS
10. Embed cover + OPF declarations
11. Verify structure

Usage:
    python docx_to_kindle_epub.py \\
        --input manuscript.docx \\
        --cover ebook_cover.jpg \\
        --output book.epub \\
        --title "Your Book Title" \\
        --subtitle "Your Subtitle" \\
        --author "Author Name" \\
        --isbn "978-X-XXXXXXX-X-X" \\
        --publisher "Your Imprint" \\
        --language "en"
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Kindle-optimized CSS
KINDLE_CSS = """@charset "utf-8";

body {
    font-family: "EB Garamond", "Bookerly", Georgia, serif;
    line-height: 1.5;
    text-align: justify;
    margin: 0;
    padding: 0;
    -webkit-hyphens: auto;
    hyphens: auto;
}

h1, h2, h3, h4 {
    font-family: "EB Garamond", Georgia, serif;
    font-weight: normal;
    text-align: center;
    page-break-after: avoid;
    page-break-before: always;
    -webkit-hyphens: none;
    hyphens: none;
}

h1 {
    font-size: 1.8em;
    margin: 2em 0 1em 0;
    font-variant: small-caps;
    letter-spacing: 0.05em;
}

h2 {
    font-size: 1.4em;
    margin: 1.5em 0 0.8em 0;
    font-style: italic;
    page-break-before: auto;
}

h3 {
    font-size: 1.2em;
    margin: 1.2em 0 0.6em 0;
    font-weight: bold;
    page-break-before: auto;
}

p {
    margin: 0 0 0.3em 0;
    text-indent: 1.5em;
    orphans: 2;
    widows: 2;
}

h1 + p, h2 + p, h3 + p,
blockquote + p,
ul + p, ol + p,
.scene-break + p,
.callout + p {
    text-indent: 0;
}

blockquote {
    margin: 1em 2em;
    padding: 0 1em;
    font-style: italic;
    border-left: 2px solid #888;
}

blockquote p {
    text-indent: 0;
    margin-bottom: 0.5em;
}

ul, ol {
    margin: 0.8em 0;
    padding-left: 2em;
}

li {
    margin-bottom: 0.4em;
}

em, i { font-style: italic; }
strong, b { font-weight: bold; }

.scene-break, p.scene-break {
    text-align: center !important;
    margin: 2em 0 !important;
    text-indent: 0 !important;
    font-size: 1.2em;
    letter-spacing: 0.5em;
    page-break-inside: avoid;
}

h2.chapter-start {
    page-break-before: always !important;
    text-align: center;
    margin: 2em 0 1em 0;
    font-size: 1.5em;
    font-variant: small-caps;
    letter-spacing: 0.08em;
    font-weight: normal;
    font-style: normal;
}

.page-break {
    page-break-before: always;
    height: 0;
    margin: 0;
    padding: 0;
    visibility: hidden;
}

.dedication-start {
    page-break-before: always !important;
    text-indent: 0;
    text-align: center;
    margin-top: 3em;
    font-style: italic;
}

/* Chapter-opening illustration — render on its own dedicated page
   (matches the print docx layout where each chariot/lotus/yantra art
   sits alone with breathing room, then the chapter title opens fresh) */
.chapter-illustration {
    page-break-before: always !important;
    page-break-after: always !important;
    text-align: center !important;
    text-indent: 0 !important;
    margin: 4em 0 0 0 !important;
    padding: 0 !important;
    width: 100% !important;
}

.chapter-illustration img {
    max-width: 70% !important;
    width: auto !important;
    height: auto !important;
    display: block !important;
    margin: 0 auto !important;
}

/* Back-matter sub-section headings (Glossary, Lineage & Gratitude,
   To the First Guru, The Kriya Yoga Lineage) — each starts a fresh page */
.back-matter-section {
    page-break-before: always !important;
    text-align: center;
    text-indent: 0;
    margin: 2em 0 1.2em;
    font-size: 1.3em;
    font-weight: bold;
    font-variant: small-caps;
    letter-spacing: 0.06em;
}

/* Only target specific subtitle classes — not all h1+p (that catches body text) */
.part-subtitle {
    text-align: center;
    text-indent: 0;
    margin-top: 0;
    margin-bottom: 1.5em;
    font-size: 0.95em;
    letter-spacing: 0.08em;
    page-break-after: avoid;
    font-weight: bold;
    font-variant: small-caps;
}

.chapter-title {
    text-align: center;
    text-indent: 0;
    margin-top: 0;
    margin-bottom: 0.5em;
    font-size: 1.05em;
    letter-spacing: 0.05em;
    page-break-after: avoid;
    font-weight: bold;
    font-variant: small-caps;
}

/* All paragraphs directly after h1 (Part headings, AUTHOR'S NOTE, etc.)
 * should have NO text-indent on first paragraph but keep normal body styling */
h1 + p, h2 + p {
    text-indent: 0;
}

/* Image immediately following blockquote or paragraph (Part opener image) */
blockquote + p:has(img),
blockquote + figure,
h2.chapter-start + p:has(img),
h2.chapter-start + figure {
    text-align: center;
    margin: 1.5em auto;
    page-break-inside: avoid;
    page-break-before: avoid;
}

/* All images centered, sized appropriately for Kindle */
img {
    display: block;
    max-width: 80%;
    height: auto;
    margin: 1.5em auto;
    page-break-inside: avoid;
    page-break-after: avoid;
}

/* Figure (semantic image wrapper) - centered with caption */
figure {
    text-align: center;
    margin: 1.5em auto;
    page-break-inside: avoid;
}

figure img {
    max-width: 80%;
    margin: 0 auto;
}

/* Image inside a paragraph that's not a figure - keep centered */
p > img {
    margin: 1em auto;
}

p:has(> img:only-child) {
    text-align: center;
    text-indent: 0;
    margin: 1.5em 0;
}

/* TOC styling */
h1 + p a, .toc a {
    text-decoration: none;
    color: inherit;
    border-bottom: 1px dotted #999;
}

.callout {
    border: 1px solid #999;
    padding: 1em 1.2em;
    margin: 1.5em 0;
    background: #f8f8f8;
    page-break-inside: avoid;
    border-radius: 4px;
}

/* First paragraph of callout = the heading (YOUR MOVE / DEEP DIVE) — center it */
.callout > p:first-child,
.callout-heading {
    font-variant: small-caps;
    letter-spacing: 0.1em;
    text-align: center !important;
    text-indent: 0 !important;
    font-weight: bold;
    margin: 0 0 0.8em 0 !important;
    font-size: 1em;
}

/* Smallcaps span inside the heading */
.callout > p:first-child .smallcaps,
.callout > p:first-child strong {
    font-variant: small-caps;
    letter-spacing: 0.1em;
}

.callout ul, .callout ol {
    margin: 0.4em 0;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
    page-break-inside: avoid;
}

figure {
    margin: 1.5em 0;
    text-align: center;
    page-break-inside: avoid;
}

figcaption {
    font-size: 0.85em;
    font-style: italic;
    margin-top: 0.5em;
    color: #555;
}

table {
    border-collapse: collapse;
    margin: 1.5em auto;
    page-break-inside: avoid;
}

th, td {
    padding: 0.4em 0.8em;
    border: 1px solid #999;
    text-align: left;
}

th {
    background: #e8e8e8;
    font-weight: bold;
}

.title-page {
    text-align: center;
    margin-top: 3em;
    page-break-after: always;
}

.title-page .book-title {
    font-size: 2.8em;
    margin-bottom: 0.3em;
    font-variant: small-caps;
    letter-spacing: 0.1em;
}

.title-page .subtitle {
    font-size: 1.3em;
    font-style: italic;
    margin-bottom: 2em;
}

.title-page .author {
    font-size: 1.1em;
    font-variant: small-caps;
    letter-spacing: 0.1em;
    margin-top: 3em;
}

.colophon {
    font-size: 0.85em;
    line-height: 1.4;
    margin-top: 4em;
}

.colophon p {
    text-indent: 0;
    margin-bottom: 0.6em;
}

.dedication {
    text-align: center;
    font-style: italic;
    margin: 4em 2em;
    page-break-before: always;
    page-break-after: always;
}

.dedication p {
    text-indent: 0;
    margin-bottom: 0.8em;
}

@media amzn-mobi {
    p { text-indent: 1.5em; }
    blockquote { margin: 1em 2em; }
}

@media amzn-kf8 {
    p { text-indent: 1.5em; }
    blockquote { margin: 1em 2em; padding-left: 1em; border-left: 2px solid #888; }
}
"""


def write_metadata_file(metadata_path, title, subtitle, author, isbn, publisher,
                        language, description, pubdate):
    """Pandoc metadata YAML."""
    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f'title: "{title}"\n')
        if subtitle:
            f.write(f'subtitle: "{subtitle}"\n')
        f.write(f'author: "{author}"\n')
        f.write(f'publisher: "{publisher}"\n')
        f.write(f'language: "{language}"\n')
        if pubdate:
            f.write(f'date: "{pubdate}"\n')
        if isbn:
            f.write(f'identifier:\n')
            f.write(f'  scheme: ISBN\n')
            f.write(f'  text: "{isbn}"\n')
        if description:
            desc_safe = description.replace('"', '\\"').replace('\n', ' ')[:500]
            f.write(f'description: "{desc_safe}"\n')
        f.write("---\n")


def run_pandoc_conversion(docx_path, epub_path, metadata_path):
    """Convert docx to EPUB 3."""
    cmd = [
        "pandoc",
        str(docx_path),
        "-o", str(epub_path),
        "-f", "docx",
        "-t", "epub3",
        "--metadata-file", str(metadata_path),
        "--epub-chapter-level=1",
        "--toc",
        "--toc-depth=2",
        "--standalone",
    ]
    print(f"  pandoc {docx_path.name if hasattr(docx_path, 'name') else docx_path} → EPUB")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Pandoc failed: {result.stderr[:500]}")


def fix_smart_quotes(html):
    """Convert straight quotes to typographic curly quotes in TEXT CONTENT only.

    Skips HTML attributes like class="...", id="...", etc.
    """
    # Split by tags — alternate between markup and text
    parts = re.split(r'(<[^>]+>)', html)
    for i, part in enumerate(parts):
        if i % 2 == 0:  # text content (even index)
            # Single quotes: opening if preceded by whitespace/start, closing otherwise
            part = re.sub(r"(^|[\s\(\[\{])'", r"\1‘", part)
            part = re.sub(r"'", r"’", part)
            # Double quotes: same logic
            part = re.sub(r'(^|[\s\(\[\{])"', r'\1“', part)
            part = re.sub(r'"', r"”", part)
            parts[i] = part
    return ''.join(parts)


def detect_and_promote_headings(html_content):
    """Find chapter markers in <p> tags and promote to <h1>/<h2>.

    STRICT match — only promote paragraphs whose text EXACTLY matches a chapter
    marker pattern. Avoids false positives on short body text.
    """
    # Patterns that indicate chapter or major-section headings
    # Each pattern must match the ENTIRE paragraph text (anchored with $)
    # Note: AUTHOR'S NOTE uses curly apostrophe ' (Unicode 2019) AFTER smart-quote pass
    chapter_patterns = [
        (r'^CHAPTER\s+\d+\.?\s*$', 1),                # "CHAPTER 1."
        (r'^Chapter\s+\d+:?\s+[A-Z][\w\s]{2,80}$', 1),# "Chapter 1: Title"
        (r'^PROLOGUE\s*$', 1),
        (r'^EPILOGUE\s*$', 1),
        (r'^PART\s+(ONE|TWO|THREE|FOUR|FIVE|[IVX]+)\s*$', 1),
        (r'^Part\s+(One|Two|Three|Four|Five|[IVX]+):?\s+[A-Z][\w\s]{2,80}$', 1),
        (r'^DEDICATION\s*$', 1),
        (r'^ACKNOWLEDGMENTS?\s*$', 1),
        (r'^ABOUT\s+THE\s+AUTHOR\s*$', 1),
        (r'^INTRODUCTION\s*$', 1),
        (r'^FOREWORD\s*$', 1),
        (r"^AUTHOR['’]?S?\s+NOTE\s*$", 1),       # AUTHOR'S NOTE (straight or curly apostrophe)
        (r'^A\s+NOTE\s+ON\s+THE\s+PHOTOGRAPHS\s*$', 1),
        (r'^A\s+NOTE\s+ON\s+THE\s+SANSKRIT\s+RENDERINGS\s*$', 1),
        (r'^JYOLING\s+ACADEMY\s*$', 1),
        (r'^JYOLING\s*$', 1),
        (r'^TABLE\s+OF\s+CONTENTS\s*$', 1),
        (r'^CONTENTS\s*$', 1),
    ]

    # Find <p> tags and check if their content matches
    def replace_p(match):
        full_p = match.group(0)
        # Extract text content
        text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
        # SKIP TOC entries — they end with a page number (" 12", " 202", etc.)
        # TOC pattern: "Chapter Title 202" — chapter title followed by space + digits at end
        if re.search(r'\s+\d{1,4}\s*$', text):
            return full_p
        # SKIP if inside a blockquote context — likely TOC or pull quote
        # (heuristic: skip if previous chars include "<blockquote")
        for pattern, level in chapter_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return f'<h{level}>{text}</h{level}>'
        return full_p

    # Process all <p>...</p>
    html_content = re.sub(r'<p[^>]*>(.+?)</p>', replace_p, html_content, flags=re.DOTALL)
    return html_content


def style_callout_boxes(html_content):
    """Wrap tables (used as callout boxes in the source docx) with .callout class.

    A common docx convention for nonfiction is to embed sidebars / call-outs
    using a 1x1 table. This function detects those tables by their first-cell
    heading text and wraps them in a div with class="callout" so the EPUB
    stylesheet can render them as proper callout boxes.

    The default keyword list below catches the common conventions; extend it
    if your manuscript uses different callout-heading text.
    """
    # Find <table> blocks and check if they look like callouts
    callout_keywords = ['YOUR MOVE', 'DEEP DIVE', 'KEY POINT', 'CALLOUT', 'SIDEBAR']

    def transform_table(match):
        table_html = match.group(0)
        # Get inner text
        inner_text = re.sub(r'<[^>]+>', ' ', table_html)[:80].upper()
        for kw in callout_keywords:
            if kw in inner_text:
                # Wrap with div.callout and convert the table to plain div
                # Extract cell content
                cells = re.findall(r'<td[^>]*>(.*?)</td>', table_html, re.DOTALL)
                if cells:
                    # First cell is the callout content
                    return f'<div class="callout">{cells[0]}</div>'
        return table_html

    return re.sub(r'<table[^>]*>.*?</table>', transform_table, html_content, flags=re.DOTALL)


def normalize_section_breaks(html_content):
    """Convert literal separator sequences to proper centered section break markers."""
    patterns = [
        r'<p[^>]*>\s*[—–-]{3,}\s*</p>',          # ——— (three em dashes)
        r'<p[^>]*>\s*\*\s*\*\s*\*\s*</p>',       # * * * or ***
        r'<p[^>]*>\s*•\s*•\s*•\s*</p>',          # • • •
        r'<p[^>]*>\s*◊\s*◊\s*◊\s*</p>',          # ◊ ◊ ◊
        r'<p[^>]*>\s*\.\s*\.\s*\.\s*</p>',       # . . .
        r'<p[^>]*>\s*•\s*•\s*•\s*</p>',  # unicode bullets
    ]
    for pat in patterns:
        html_content = re.sub(
            pat,
            '<p class="scene-break">◊ ◊ ◊</p>',
            html_content
        )
    return html_content


def detect_chapter_subheadings(html_content):
    """Detect 'CHAPTER N' and chapter title patterns inside parts, promote to H2.

    Looks for paragraphs like:
        <p><strong>CHAPTER 1</strong></p>
        <p><strong>THE ALARM BELLS ARE RINGING</strong></p>
    and promotes the CHAPTER N to <h2 class="chapter-start">.

    Adds page-break-before via CSS.
    """
    chapter_num_pattern = re.compile(
        r'<p[^>]*>\s*(?:<strong>|<b>)?\s*CHAPTER\s+\d+\.?\s*(?:</strong>|</b>)?\s*</p>',
        re.IGNORECASE
    )

    chapter_id_counter = [0]
    def promote(match):
        chapter_id_counter[0] += 1
        # Extract chapter number from text
        text = re.sub(r'<[^>]+>', '', match.group(0)).strip()
        # Use text like "CHAPTER 1"
        ch_id = f'chapter-{chapter_id_counter[0]}'
        return f'<h2 id="{ch_id}" class="chapter-start">{text}</h2>'

    html_content = chapter_num_pattern.sub(promote, html_content)
    return html_content


def tag_part_and_chapter_subtitles(html_content):
    """Add class='part-subtitle' to short uppercase paragraph after H1 PART.
    Add class='chapter-title' to bold paragraph after H2.chapter-start.

    Only short, all-caps paragraphs get these classes — body prose is left alone.
    """
    # After H1 PART → next <p> (with optional inner tags like <strong>) → part-subtitle
    pattern_part = re.compile(
        r'(<h1[^>]*>\s*PART\s+[IVX]+\s*</h1>\s*)(<p[^>]*>)((?:<strong>|<b>|<em>|<i>)?[^<]{1,60}(?:</strong>|</b>|</em>|</i>)?)(</p>)',
        re.IGNORECASE
    )

    def tag_part(match):
        h1, p_open, p_text, p_close = match.groups()
        # Strip inner tags to check uppercase
        plain = re.sub(r'<[^>]+>', '', p_text).strip()
        if plain and (plain.isupper() or sum(1 for c in plain if c.isupper()) / max(len([c for c in plain if c.isalpha()]), 1) > 0.7):
            if 'class=' not in p_open:
                p_open = p_open.replace('<p', '<p class="part-subtitle"', 1)
            else:
                p_open = re.sub(r'class="([^"]*)"', r'class="\1 part-subtitle"', p_open)
        return h1 + p_open + p_text + p_close

    html_content = pattern_part.sub(tag_part, html_content)

    # After H2.chapter-start → next <p> with bold/uppercase text → chapter-title
    pattern_chapter = re.compile(
        r'(<h2[^>]*class="[^"]*chapter-start[^"]*"[^>]*>[^<]+</h2>\s*)(<p[^>]*>)((?:<strong>|<b>)?[^<]{1,80}(?:</strong>|</b>)?)(</p>)'
    )

    def tag_chapter(match):
        h2, p_open, p_text, p_close = match.groups()
        # Extract plain text
        plain = re.sub(r'<[^>]+>', '', p_text).strip()
        # Only if all-caps or starts with strong
        if plain and (plain.isupper() or '<strong>' in p_text or '<b>' in p_text):
            if 'class=' not in p_open:
                p_open = p_open.replace('<p', '<p class="chapter-title"', 1)
            else:
                p_open = re.sub(r'class="([^"]*)"', r'class="\1 chapter-title"', p_open)
        return h2 + p_open + p_text + p_close

    html_content = pattern_chapter.sub(tag_chapter, html_content)
    return html_content


def detect_dedication_break(html_content, dedication_first_line=None):
    """Add a page break before the dedication paragraph.

    Books typically have a dedication that follows the copyright/colophon. To
    force a clean page break before it, supply the exact opening phrase of the
    dedication via the `dedication_first_line` argument (e.g. "Storms came from
    every direction" or "For my mother"). The function finds the paragraph
    starting with that phrase and wraps it with class="dedication-start".

    If `dedication_first_line` is None or empty, the function is a no-op —
    Pandoc's default page breaks remain in place.
    """
    if not dedication_first_line:
        return html_content

    pattern = re.compile(
        r'(<p[^>]*>)(\s*(?:<em>|<i>)?\s*' + re.escape(dedication_first_line) + r'[^<]*)',
        re.IGNORECASE
    )

    def add_break(match):
        opening = match.group(1)
        if 'class=' in opening:
            opening = re.sub(r'class="([^"]*)"', r'class="\1 dedication-start"', opening)
        else:
            opening = opening.replace('<p', '<p class="dedication-start"', 1)
        return '<div class="page-break"></div>' + opening + match.group(2)

    return pattern.sub(add_break, html_content, count=1)


def isolate_chapter_illustrations(html_content):
    """Wrap chapter-opening illustrations on their own dedicated page.

    Pandoc places each chapter's illustration as a <p><img/></p> directly
    before the <h2 class="chapter-start"> heading. On reflow that bunches the
    image and chapter title onto the same Kindle page, which crowds the
    opener. The print docx renders the illustration on its own page with
    white space below — we want the same feel here.

    We wrap the image paragraph with class="chapter-illustration" so its CSS
    rule (page-break-before AND page-break-after: always) gives it a clean
    dedicated page; the chapter heading then opens fresh on the next page.
    """
    pattern = re.compile(
        r'(<p[^>]*>)(<img[^>]*/?>)(</p>)(\s*<h2[^>]*class="[^"]*chapter-start)',
        re.IGNORECASE
    )

    def wrap(match):
        p_open, img, p_close, h2_tail = match.groups()
        # Inject the chapter-illustration class
        if 'class=' in p_open:
            p_open = re.sub(r'class="([^"]*)"', r'class="\1 chapter-illustration"', p_open)
        else:
            p_open = p_open.replace('<p', '<p class="chapter-illustration"', 1)
        return p_open + img + p_close + h2_tail

    return pattern.sub(wrap, html_content)


def promote_back_matter_sections(html_content, section_markers=None):
    """Promote specific back-matter sub-section markers to H2 with page-break-before.

    Some books have back-matter sub-sections (Glossary, Acknowledgments groups,
    Dedications, Lineage notes) that arrive from Word as bold paragraphs but
    deserve their own page in the EPUB. Pass a list of exact text markers
    (e.g. ['Glossary', 'Acknowledgments', 'About the Author']) and each one
    will be promoted to <h2 class="back-matter-section"> with a page break.

    If `section_markers` is None or empty, the function is a no-op.
    """
    if not section_markers:
        return html_content

    # HTML-entity-encode ampersands automatically so callers can write "Lineage & Gratitude"
    expanded_markers = []
    for m in section_markers:
        expanded_markers.append(m)
        if '&' in m and '&amp;' not in m:
            expanded_markers.append(m.replace('&', '&amp;'))

    for marker in expanded_markers:
        pattern = re.compile(
            r'<p[^>]*>\s*<strong>\s*' + re.escape(marker) + r'\s*</strong>\s*</p>',
            re.IGNORECASE
        )
        replacement = f'<h2 class="back-matter-section">{marker}</h2>'
        html_content = pattern.sub(replacement, html_content, count=1)

    return html_content


def balance_section_tags(html_content):
    """Auto-balance <section> tags within a single document.

    Properly handles both COUNT mismatches AND ORDER mismatches (orphan
    closing tags that appear before any opening tag). This is critical for
    Pandoc-split content where </section> may be left over from a parent
    section that was split away.
    """
    # Walk through the body tag-by-tag tracking depth
    body_match = re.search(r'(<body[^>]*>)(.*?)(</body>)', html_content, re.DOTALL)
    if not body_match:
        return html_content

    body_open = body_match.group(1)
    body_content = body_match.group(2)
    body_close = body_match.group(3)

    # Find all <section> and </section> positions
    section_pattern = re.compile(r'(<section\b[^>]*>)|(</section>)')
    depth = 0
    to_remove = []  # positions of orphan closing tags

    for m in section_pattern.finditer(body_content):
        if m.group(1):  # opening
            depth += 1
        else:  # closing
            if depth == 0:
                # Orphan closing — mark for removal
                to_remove.append((m.start(), m.end()))
            else:
                depth -= 1

    # Remove orphan closing tags (reverse order to preserve positions)
    for start, end in reversed(to_remove):
        body_content = body_content[:start] + body_content[end:]

    # Now if depth > 0, we have unclosed sections — append closing tags
    if depth > 0:
        body_content = body_content + ('</section>' * depth)

    return html_content[:body_match.start()] + body_open + body_content + body_close + html_content[body_match.end():]


def linkify_toc_entries(html_content):
    """Find CONTENTS section in HTML and wrap chapter entries with <a href> links.

    Finds paragraphs containing "Chapter N Title XX" and wraps them with
    hyperlinks pointing to chapter-N IDs.

    STRICT — a paragraph qualifies as a TOC entry only when ALL of these hold:
      - Total text length ≤ 90 chars (TOC lines are short)
      - Ends with a trailing page number (TOC lines always carry page refs)
    This prevents body paragraphs that happen to begin with "Chapter N …" from
    being wrapped as broken internal hyperlinks.
    """
    # Only process if "CONTENTS" h1 is present
    if not re.search(r'<h1[^>]*>\s*CONTENTS\s*</h1>', html_content, re.IGNORECASE):
        return html_content

    # Find paragraphs that look like TOC entries: "Chapter N Title page-number"
    toc_entry_pattern = re.compile(
        r'(<p[^>]*>\s*(?:<em>|<i>)?)\s*(Chapter\s+(\d+)\s+[^<]+?)\s*(?:</em>|</i>)?\s*</p>',
        re.IGNORECASE
    )

    def linkify(match):
        prefix = match.group(1)
        chapter_text = match.group(2).strip()
        chapter_num = match.group(3)
        # Hard requirement: TOC lines are short AND end with a page number
        if len(chapter_text) > 90:
            return match.group(0)
        if not re.search(r'\s+\d{1,4}\s*$', chapter_text):
            return match.group(0)
        return f'{prefix}<a href="#chapter-{chapter_num}">{chapter_text}</a></p>'

    return toc_entry_pattern.sub(linkify, html_content)


def wrap_images_in_figures(html_content):
    """Wrap orphan <img> tags in <figure>."""
    # Match <p><img .../></p> and convert to <figure><img .../></figure>
    html_content = re.sub(
        r'<p[^>]*>\s*(<img[^/]*/?>)\s*</p>',
        r'<figure>\1</figure>',
        html_content
    )
    return html_content


def clean_title_page_duplicates(html_content, title=None, subtitle=None, subtitle2=None, author=None):
    """Replace messy title-page duplication at the start of the body.

    Pandoc often repeats the title/subtitle/author across the first several
    paragraphs after the <body> opens. This function detects the messy block
    (everything before the first <p>Copyright… paragraph) and replaces it
    with a clean title-page div using the supplied book metadata.

    Parameters:
      title:     book title (required for the replacement to fire)
      subtitle:  optional subtitle line
      subtitle2: optional second subtitle line (e.g., series/edition)
      author:    optional author name

    If `title` is None, the function is a no-op.
    """
    if not title:
        return html_content

    # Find the first occurrence of body content before <p>Copyright
    match = re.search(r'<body[^>]*>(.*?)<p>Copyright', html_content, re.DOTALL)
    if not match:
        return html_content

    head_section = match.group(1)

    # Build a clean title page from the supplied metadata
    lines = [f'<p class="book-title">{title}</p>']
    if subtitle:
        lines.append(f'<p class="subtitle">{subtitle}</p>')
    if subtitle2:
        lines.append(f'<p class="subtitle">{subtitle2}</p>')
    if author:
        lines.append(f'<p class="author">{author}</p>')
    clean_title = '<div class="title-page">\n' + '\n'.join(lines) + '\n</div>\n'

    return html_content.replace(head_section, clean_title, 1)


def split_into_chapters(xhtml_path, output_dir):
    """Split the monolithic xhtml into per-chapter files at H1 boundaries.

    Only splits where the H1 is at the top level (not nested inside other blocks
    like blockquote, table, etc.) to avoid breaking element boundaries.

    Returns list of new file paths.
    """
    with open(xhtml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract head section (everything before <body>)
    head_match = re.search(r'(.*?<body[^>]*>)', content, re.DOTALL)
    if not head_match:
        return [xhtml_path]
    head = head_match.group(1)
    body_inner = content[head_match.end():content.rfind('</body>')]

    # Find SAFE H1 split points — H1s that are NOT inside any unclosed block
    # element. Walk forward tracking depth of blockquote/div/table/section.
    split_positions = [0]
    pos = 0
    depth_blockquote = 0
    depth_table = 0
    depth_section = 0

    # Tokenize on tags
    for match in re.finditer(r'<(/?)(\w+)[^>]*>', body_inner):
        tag = match.group(2).lower()
        closing = match.group(1) == '/'
        # Track block-element depth
        if tag == 'blockquote':
            depth_blockquote += -1 if closing else 1
        elif tag == 'table':
            depth_table += -1 if closing else 1
        elif tag == 'section':
            depth_section += -1 if closing else 1
        # If H1 opening at top level, mark as split point
        if tag == 'h1' and not closing:
            if depth_blockquote == 0 and depth_table == 0 and depth_section == 0:
                split_positions.append(match.start())

    # Add end position
    split_positions.append(len(body_inner))
    # Dedup + sort
    split_positions = sorted(set(split_positions))

    if len(split_positions) <= 2:  # only beginning + end → no real splits
        return [xhtml_path]

    # Build chapters from split positions
    chapters = []
    for i in range(len(split_positions) - 1):
        chunk = body_inner[split_positions[i]:split_positions[i+1]].strip()
        if chunk:
            chapters.append(chunk)

    if len(chapters) <= 1:
        return [xhtml_path]

    # Adjust head's <title> for each chapter
    new_files = []
    for i, chapter in enumerate(chapters):
        # Extract heading text for title and filename
        h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', chapter)
        title = h1_match.group(1).strip() if h1_match else f'Section {i+1}'
        # Sanitize for filename
        safe_title = re.sub(r'[^a-z0-9]+', '_', title.lower())[:40].strip('_') or f'section_{i+1}'

        new_name = f'ch{i+1:03d}_{safe_title}.xhtml'
        new_path = os.path.join(output_dir, new_name)

        # Replace <title> in head with chapter title
        chapter_head = re.sub(
            r'<title>[^<]*</title>',
            f'<title>{title}</title>',
            head,
            count=1
        )

        # Write chapter file
        chapter_content = chapter_head + chapter + '\n</body>\n</html>\n'
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(chapter_content)
        new_files.append(new_path)

    # Remove original monolithic file
    os.remove(xhtml_path)
    return new_files


def rebuild_navigation(content_root, opf_path, book_title=None):
    """Rebuild nav.xhtml (EPUB 3) and toc.ncx (EPUB 2) from actual chapter files.

    Pandoc generates a minimal nav with one entry pointing to the original
    monolithic file — after split_into_chapters() removes that file, both
    nav.xhtml and toc.ncx contain broken references. KDP rejects the upload
    with "broken link in your Table of Contents".

    This pass reads the post-split OPF spine, extracts each chapter file's
    first H1 as its display title, and writes fresh nav.xhtml + toc.ncx with
    one TOC entry per chapter. Cover, nav, and title page are excluded from
    the visible TOC (they're not user-navigable).

    Returns (chapter_count, nav_path) so the caller can confirm + log.
    """
    # Parse OPF to get spine order + manifest hrefs + (fallback) title
    with open(opf_path, 'r', encoding='utf-8') as f:
        opf = f.read()

    spine_ids = re.findall(r'<itemref\s+idref="([^"]+)"', opf)
    manifest = {}
    for m in re.finditer(r'<item\s+id="([^"]+)"\s+href="([^"]+)"', opf):
        manifest[m.group(1)] = m.group(2)

    # Resolve book title — prefer caller-supplied, else pull from OPF
    if not book_title:
        t_match = re.search(r'<dc:title[^>]*>([^<]+)</dc:title>', opf)
        book_title = t_match.group(1).strip() if t_match else 'Book'

    # Identifiers to skip in TOC (cover + nav are not user-facing TOC entries)
    skip_ids = {'cover-page', 'nav', 'ncx'}

    toc_entries = []  # list of (href_relative_to_nav, label)
    for sid in spine_ids:
        if sid in skip_ids:
            continue
        href = manifest.get(sid)
        if not href:
            continue
        # Resolve chapter file path
        chapter_path = os.path.join(content_root, href)
        if not os.path.exists(chapter_path):
            continue
        with open(chapter_path, 'r', encoding='utf-8') as f:
            ch_content = f.read()
        # Extract first H1 as label (non-greedy — stop at FIRST </h1>)
        h_match = re.search(r'<h1\b[^>]*>(.*?)</h1>', ch_content, re.DOTALL)
        if h_match:
            # Strip any inner tags + collapse whitespace
            raw = re.sub(r'<[^>]+>', '', h_match.group(1))
            label = re.sub(r'\s+', ' ', raw).strip()
        else:
            # No H1 = unsplittable interstitial (title page, dedication, copyright).
            # Skip it from the TOC entirely — the title_page entry already covers it,
            # and a generic "Section 1" link confuses readers and KDP reviewers.
            continue
        if not label:
            continue
        toc_entries.append((href, label))

    # --- Build nav.xhtml (EPUB 3) ---
    nav_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE html>',
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">',
        '<head>',
        '  <meta charset="utf-8" />',
        f'  <title>{book_title}</title>',
        '  <link rel="stylesheet" type="text/css" href="styles/kindle.css" />',
        '</head>',
        '<body>',
        '<nav epub:type="toc" id="toc">',
        '  <h1>Contents</h1>',
        '  <ol class="toc">',
    ]
    for i, (href, label) in enumerate(toc_entries):
        # Escape any & in label for XHTML
        safe_label = label.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        nav_lines.append(f'    <li id="toc-li-{i+1}"><a href="{href}">{safe_label}</a></li>')
    nav_lines.extend([
        '  </ol>',
        '</nav>',
        '<nav epub:type="landmarks" id="landmarks" hidden="hidden">',
        '  <ol>',
        '    <li><a href="#toc" epub:type="toc">Table of contents</a></li>',
        '  </ol>',
        '</nav>',
        '</body>',
        '</html>',
    ])
    nav_path = os.path.join(content_root, 'nav.xhtml')
    with open(nav_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(nav_lines))

    # --- Build toc.ncx (EPUB 2 fallback) ---
    # Extract uid (ISBN) from existing ncx if possible
    uid = ''
    ncx_path = os.path.join(content_root, 'toc.ncx')
    if os.path.exists(ncx_path):
        with open(ncx_path, 'r', encoding='utf-8') as f:
            old_ncx = f.read()
        u_match = re.search(r'<meta\s+name="dtb:uid"\s+content="([^"]+)"', old_ncx)
        if u_match:
            uid = u_match.group(1)

    ncx_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">',
        '  <head>',
        f'    <meta name="dtb:uid" content="{uid}" />',
        '    <meta name="dtb:depth" content="1" />',
        '    <meta name="dtb:totalPageCount" content="0" />',
        '    <meta name="dtb:maxPageNumber" content="0" />',
        '  </head>',
        '  <docTitle>',
        f'    <text>{book_title}</text>',
        '  </docTitle>',
        '  <navMap>',
    ]
    for i, (href, label) in enumerate(toc_entries):
        safe_label = label.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        ncx_lines.extend([
            f'    <navPoint id="navPoint-{i+1}" playOrder="{i+1}">',
            '      <navLabel>',
            f'        <text>{safe_label}</text>',
            '      </navLabel>',
            f'      <content src="{href}" />',
            '    </navPoint>',
        ])
    ncx_lines.extend([
        '  </navMap>',
        '</ncx>',
    ])
    with open(ncx_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ncx_lines))

    return len(toc_entries), nav_path


def fix_cross_file_anchors(content_root):
    """Rewrite same-file href="#anchor" links to cross-file href="file.xhtml#anchor".

    Before the EPUB is split, the CONTENTS page contains links like
    <a href="#chapter-7">…</a> that work because the entire book is one file.
    After split_into_chapters() carves the book into separate XHTML files,
    those #anchor links become broken — KDP correctly rejects them.

    This pass walks every XHTML file twice:
      1. Build a map: anchor_id → filename where it lives
      2. Rewrite each <a href="#anchor"> so it points to the correct file
         (only when the anchor lives in a different file from the link)

    Returns the count of links fixed.
    """
    text_files = []
    for root, _, files in os.walk(content_root):
        for fname in files:
            if fname.endswith(('.xhtml', '.html')):
                text_files.append(os.path.join(root, fname))

    # Pass 1: map every id="…" to its containing file basename
    id_to_file = {}
    for fpath in text_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        basename = os.path.basename(fpath)
        for m in re.finditer(r'\sid="([^"]+)"', content):
            id_to_file[m.group(1)] = basename

    # Set of all known XHTML basenames (for detecting stale filename refs)
    known_files = {os.path.basename(f) for f in text_files}

    # Pass 2: rewrite hrefs
    fixed_count = 0
    for fpath in text_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        current_basename = os.path.basename(fpath)
        changed = False

        def rewrite_same_file(match):
            nonlocal fixed_count, changed
            anchor = match.group(1)
            target_file = id_to_file.get(anchor)
            if target_file and target_file != current_basename:
                fixed_count += 1
                changed = True
                return f'href="{target_file}#{anchor}"'
            return match.group(0)

        def rewrite_cross_file(match):
            nonlocal fixed_count, changed
            full_href = match.group(1)
            # Split into path and anchor
            if '#' in full_href:
                path_part, anchor = full_href.split('#', 1)
            else:
                path_part, anchor = full_href, ''
            # Get just the basename (strip directories like "text/")
            ref_basename = os.path.basename(path_part)
            # If the referenced file doesn't exist but the anchor lives somewhere, retarget
            if ref_basename and ref_basename not in known_files and anchor:
                target_file = id_to_file.get(anchor)
                if target_file:
                    fixed_count += 1
                    changed = True
                    # Preserve the directory prefix from the original href if present
                    dir_prefix = os.path.dirname(path_part)
                    new_path = f'{dir_prefix}/{target_file}' if dir_prefix else target_file
                    return f'href="{new_path}#{anchor}"'
            return match.group(0)

        new_content = re.sub(r'href="#([^"]+)"', rewrite_same_file, content)
        new_content = re.sub(r'href="([^"#][^"]*#[^"]+)"', rewrite_cross_file, new_content)
        if changed:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)

    return fixed_count


def update_opf_for_split(opf_path, chapter_files, content_root):
    """Update OPF to list chapters in manifest and spine.

    Removes references to the old monolithic ch001 file and inserts
    references for each new chapter file.
    """
    with open(opf_path, "r", encoding="utf-8") as f:
        opf = f.read()

    # Build new manifest items + spine entries
    new_items = []
    new_spine = []
    for i, fpath in enumerate(chapter_files):
        rel = os.path.relpath(fpath, content_root).replace(os.sep, '/')
        item_id = f'chapter-{i+1:03d}'
        new_items.append(f'<item id="{item_id}" href="{rel}" media-type="application/xhtml+xml"/>')
        new_spine.append(f'<itemref idref="{item_id}"/>')

    # Remove ALL manifest items referencing old ch001 (any naming variant)
    # Matches: <item ... href="text/ch001.xhtml" .../>
    opf = re.sub(
        r'\s*<item\s+[^>]*href="[^"]*ch001[^"]*\.xhtml"[^>]*/?>\s*\n?',
        '',
        opf
    )

    # Remove ALL spine itemrefs referencing old ch001 by any id variant
    # The id might be "ch001_xhtml" or "ch001.xhtml" or similar
    opf = re.sub(
        r'\s*<itemref\s+idref="[^"]*ch001[^"]*"[^/]*/?>\s*\n?',
        '',
        opf
    )

    # Insert new manifest items at end of manifest
    manifest_block = '\n    '.join(new_items)
    opf = opf.replace('</manifest>', f'    {manifest_block}\n</manifest>')

    # Insert new spine entries at end of spine
    spine_block = '\n    '.join(new_spine)
    opf = opf.replace('</spine>', f'    {spine_block}\n</spine>')

    with open(opf_path, "w", encoding="utf-8") as f:
        f.write(opf)


def process_epub_content(epub_path, cover_path=None,
                         title=None, subtitle=None, subtitle2=None, author=None,
                         dedication_first_line=None, back_matter_markers=None):
    """Main post-processing: unzip, apply all fixes, rezip."""
    temp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(epub_path, 'r') as zf:
            zf.extractall(temp_dir)

        # Find OPF
        content_root = None
        opf_path = None
        for root, dirs, files in os.walk(temp_dir):
            for fname in files:
                if fname.endswith('.opf'):
                    content_root = root
                    opf_path = os.path.join(root, fname)
                    break
            if content_root:
                break

        if not content_root:
            print(f"  ⚠ Could not find OPF directory")
            return

        # Inject CSS file
        styles_dir = os.path.join(content_root, "styles")
        os.makedirs(styles_dir, exist_ok=True)
        css_path = os.path.join(styles_dir, "kindle.css")
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(KINDLE_CSS)

        # Process every XHTML
        all_xhtml = []
        for root, _, files in os.walk(content_root):
            for fname in files:
                if fname.endswith(('.xhtml', '.html')):
                    all_xhtml.append(os.path.join(root, fname))

        for xpath in all_xhtml:
            with open(xpath, "r", encoding="utf-8") as f:
                content = f.read()

            # Apply transformations IN ORDER:
            # 1. Clean title page FIRST (removes duplicate title-fragment paragraphs
            #    that would otherwise be promoted to H1 by detect_and_promote_headings)
            content = clean_title_page_duplicates(content, title=title, subtitle=subtitle,
                                                  subtitle2=subtitle2, author=author)
            # 2. Smart quotes (skips HTML attributes) — converts ' to ' BEFORE
            #    heading detection so AUTHOR'S NOTE pattern can match
            content = fix_smart_quotes(content)
            # 3. Detect Part-level headings and promote to H1
            content = detect_and_promote_headings(content)
            # 4. Detect CHAPTER N within parts and promote to H2 with page-break-before
            content = detect_chapter_subheadings(content)
            # 4a. Tag Part subtitles and Chapter titles with proper classes
            content = tag_part_and_chapter_subtitles(content)
            # 5. Add page break before the dedication (no-op if no dedication_first_line supplied)
            content = detect_dedication_break(content, dedication_first_line=dedication_first_line)
            # 5a. Promote back-matter sub-section markers — no-op if no markers supplied
            content = promote_back_matter_sections(content, section_markers=back_matter_markers)
            # 5b. Give each chapter-opening illustration its own dedicated page
            content = isolate_chapter_illustrations(content)
            # 6. Linkify CONTENTS table-of-contents entries (creates clickable TOC)
            content = linkify_toc_entries(content)
            # 7. Style callout boxes
            content = style_callout_boxes(content)
            # 8. Wrap orphan images in figures
            content = wrap_images_in_figures(content)
            # 9. Normalize section breaks (catches • • • now)
            content = normalize_section_breaks(content)
            # 10. Auto-balance <section> tags (prevents XHTML parser errors)
            content = balance_section_tags(content)

            # Strip MsoNormal etc.
            content = re.sub(r'\sclass="Mso\w*"', '', content)

            # Link CSS
            if 'kindle.css' not in content:
                rel_to_css = os.path.relpath(css_path, os.path.dirname(xpath)).replace(os.sep, '/')
                link_tag = f'<link rel="stylesheet" type="text/css" href="{rel_to_css}"/>\n</head>'
                content = content.replace('</head>', link_tag)

            with open(xpath, "w", encoding="utf-8") as f:
                f.write(content)

        # Add CSS to manifest
        with open(opf_path, "r", encoding="utf-8") as f:
            opf_content = f.read()
        if 'kindle.css' not in opf_content:
            manifest_item = '<item id="kindle-style" href="styles/kindle.css" media-type="text/css"/>\n'
            opf_content = opf_content.replace('</manifest>', manifest_item + '</manifest>')
            with open(opf_path, "w", encoding="utf-8") as f:
                f.write(opf_content)

        # Split monolithic chapter into multiple files
        main_xhtml = None
        for xpath in all_xhtml:
            if 'ch001.xhtml' in xpath:
                main_xhtml = xpath
                break

        if main_xhtml:
            text_dir = os.path.dirname(main_xhtml)
            new_chapters = split_into_chapters(main_xhtml, text_dir)
            if len(new_chapters) > 1:
                update_opf_for_split(opf_path, new_chapters, content_root)
                # Post-split: balance section tags in each new chapter file
                for ch_path in new_chapters:
                    with open(ch_path, 'r', encoding='utf-8') as f:
                        ch_content = f.read()
                    ch_content_fixed = balance_section_tags(ch_content)
                    if ch_content_fixed != ch_content:
                        with open(ch_path, 'w', encoding='utf-8') as f:
                            f.write(ch_content_fixed)
                # Post-split: rewrite same-file #anchor links to cross-file links
                # (KDP rejects EPUBs whose TOC links point to anchors in OTHER files
                # via "#anchor" rather than "file.xhtml#anchor")
                fixed_links = fix_cross_file_anchors(content_root)
                # Post-split: rebuild nav.xhtml + toc.ncx so the EPUB's internal
                # navigation actually points at the post-split chapter files,
                # not the deleted monolithic ch001.xhtml
                nav_count, _ = rebuild_navigation(content_root, opf_path)
                print(f"  ✓ Split into {len(new_chapters)} chapter files + tag-balanced + {fixed_links} cross-file links rewritten + nav.xhtml/toc.ncx rebuilt ({nav_count} TOC entries)")

        # Add cover
        if cover_path and os.path.exists(cover_path):
            with open(cover_path, "rb") as f:
                cover_data = f.read()

            images_dir = os.path.join(content_root, "images")
            os.makedirs(images_dir, exist_ok=True)
            with open(os.path.join(images_dir, "cover.jpg"), "wb") as f:
                f.write(cover_data)

            # Create cover.xhtml
            cover_xhtml = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Cover</title>
  <meta charset="utf-8"/>
  <style type="text/css">
    body { margin: 0; padding: 0; text-align: center; }
    img { max-width: 100%; height: auto; }
  </style>
</head>
<body epub:type="cover">
  <div><img src="images/cover.jpg" alt="Cover"/></div>
</body>
</html>"""
            with open(os.path.join(content_root, "cover.xhtml"), "w", encoding="utf-8") as f:
                f.write(cover_xhtml)

            # Update OPF
            with open(opf_path, "r", encoding="utf-8") as f:
                opf_content = f.read()

            if 'images/cover.jpg' not in opf_content:
                cover_items = (
                    '<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>\n'
                    '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>\n'
                )
                opf_content = opf_content.replace('</manifest>', cover_items + '</manifest>')

                opf_content = re.sub(
                    r'(<spine[^>]*>)',
                    r'\1\n    <itemref idref="cover-page" linear="no"/>',
                    opf_content
                )

                if '<meta name="cover"' not in opf_content:
                    opf_content = re.sub(
                        r'(</metadata>)',
                        '<meta name="cover" content="cover-image"/>\n\\1',
                        opf_content
                    )

                with open(opf_path, "w", encoding="utf-8") as f:
                    f.write(opf_content)

        # Rezip EPUB
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            mimetype_path = os.path.join(temp_dir, "mimetype")
            if os.path.exists(mimetype_path):
                zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            for root, _, files in os.walk(temp_dir):
                for fname in files:
                    if fname == "mimetype":
                        continue
                    fpath = os.path.join(root, fname)
                    arcname = os.path.relpath(fpath, temp_dir).replace(os.sep, '/')
                    zf.write(fpath, arcname)

        print(f"  ✓ All post-processing complete")
    finally:
        shutil.rmtree(temp_dir)


def verify_epub(epub_path):
    """Verification."""
    with zipfile.ZipFile(epub_path, 'r') as zf:
        names = zf.namelist()
        # Count chapters
        chapter_count = sum(1 for n in names if re.match(r'.*ch\d+_.*\.xhtml', n) or 'ch001' in n)

    has_mimetype = "mimetype" in names
    has_container = any("container.xml" in n for n in names)
    has_opf = any(n.endswith('.opf') for n in names)
    has_cover = any('cover' in n.lower() and (n.endswith('.jpg') or n.endswith('.xhtml')) for n in names)
    has_toc = any(n.endswith('.ncx') or 'nav.xhtml' in n for n in names)

    print(f"\n  === EPUB Structure Verification ===")
    print(f"  mimetype:    {'✓' if has_mimetype else '✗'}")
    print(f"  container:   {'✓' if has_container else '✗'}")
    print(f"  OPF package: {'✓' if has_opf else '✗'}")
    print(f"  Cover:       {'✓' if has_cover else '✗'}")
    print(f"  TOC:         {'✓' if has_toc else '✗'}")
    print(f"  Chapter files: {chapter_count}")

    size_mb = os.path.getsize(epub_path) / (1024 * 1024)
    print(f"  File size:   {size_mb:.1f} MB")

    return all([has_mimetype, has_container, has_opf, has_cover, has_toc])


def main():
    p = argparse.ArgumentParser(description="Convert docx to Kindle-ready EPUB")
    p.add_argument("--input", required=True, help="Input .docx file")
    p.add_argument("--output", required=True, help="Output .epub file")
    p.add_argument("--cover", help="Cover image (1600×2560 JPG)")
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--subtitle2", default="",
                   help="Optional second subtitle line for the title page (e.g., a series tagline)")
    p.add_argument("--author", required=True)
    p.add_argument("--isbn", default="")
    p.add_argument("--publisher", default="")
    p.add_argument("--language", default="en")
    p.add_argument("--description", default="")
    p.add_argument("--pubdate", default="")
    p.add_argument("--dedication-first-line", default="",
                   help="Exact opening phrase of the dedication paragraph (forces a "
                        "page break before it). Example: 'For my mother' or 'Storms came…'")
    p.add_argument("--back-matter-marker", action="append", default=[],
                   help="Bold-text section header to promote to H2 with a page break "
                        "(repeatable). Example: --back-matter-marker 'Glossary' "
                        "--back-matter-marker 'Acknowledgments'")
    args = p.parse_args()

    print(f"\n=== Kindle EPUB Pipeline ===")
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}\n")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        metadata_path = f.name
    try:
        write_metadata_file(
            metadata_path,
            args.title, args.subtitle, args.author, args.isbn,
            args.publisher, args.language, args.description, args.pubdate
        )
        print(f"Step 1: Metadata YAML written")

        print(f"Step 2: Pandoc conversion")
        run_pandoc_conversion(args.input, args.output, metadata_path)

        print(f"Step 3: Post-processing (smart quotes, headings, splits, CSS, cover)")
        process_epub_content(
            args.output, args.cover,
            title=args.title,
            subtitle=args.subtitle or None,
            subtitle2=args.subtitle2 or None,
            author=args.author,
            dedication_first_line=args.dedication_first_line or None,
            back_matter_markers=args.back_matter_marker or None,
        )

        print(f"Step 4: Verification")
        ok = verify_epub(args.output)

        print(f"\n=== DONE ===")
        print(f"Output: {args.output}")
        print(f"Status: {'✓ Ready for Kindle upload' if ok else '⚠ Review before upload'}")
    finally:
        try:
            os.unlink(metadata_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
