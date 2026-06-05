"""
KDP Metadata Pre-flight Validation.

Validates title, subtitle, description, keywords, categories against KDP rules.
Reads a JSON or YAML config file with all metadata fields.

Usage:
    python validate_metadata.py path/to/metadata.json

Example metadata.json:
{
    "title": "Your Book Title",
    "subtitle": "Your Subtitle — Optional Second Line",
    "author_first": "FirstName",
    "author_last": "LastName",
    "description": "Your KDP description, up to 4000 characters with allowed HTML...",
    "keywords": ["keyword phrase one", "keyword phrase two", "..."],
    "categories": ["Books > Fiction > Literary", "Books > Self-Help > Personal Growth", "..."],
    "isbn": "978-X-XXXXXXX-X-X",
    "price_usd": 14.99,
    "page_count": 250,
    "paper_type": "bw_white",
    "trim": "5.5x8.5"
}
"""

import argparse
import json
import re
import sys

# KDP limits
TITLE_MAX = 200
SUBTITLE_MAX = 200
DESCRIPTION_MAX = 4000
KEYWORD_MAX_LENGTH = 50
KEYWORD_MAX_COUNT = 7
ALLOWED_HTML_TAGS = {"br", "b", "i", "em", "strong", "u", "ol", "ul", "li",
                     "h4", "h5", "h6", "p"}
BANNED_DESCRIPTION_PHRASES = [
    r"\bbestseller\b", r"\bbest[- ]selling\b", r"\b#1 in\b",
    r"\bfree\b(?!\s*shipping)", r"\bgo to my site\b",
    r"\bcontact me at\b", r"\bemail me\b",
    r"\bcall\b.*\b\d{3}",
]
BANNED_KEYWORD_TERMS = [
    "bestseller", "best selling", "free", "kindle unlimited",
]


def check_url_in_description(desc):
    """Find URLs in description (most aren't allowed)."""
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    return re.findall(url_pattern, desc)


def check_email_in_description(desc):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(email_pattern, desc)


def check_phone_in_description(desc):
    phone_pattern = r'\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}'
    return re.findall(phone_pattern, desc)


def check_html_tags_in_description(desc):
    tag_pattern = r'<(/?)(\w+)[^>]*>'
    found_tags = set()
    invalid_tags = set()
    for m in re.finditer(tag_pattern, desc):
        tag = m.group(2).lower()
        found_tags.add(tag)
        if tag not in ALLOWED_HTML_TAGS:
            invalid_tags.add(tag)
    return found_tags, invalid_tags


def check_min_price(page_count, paper_type="bw_white"):
    """KDP minimum royalty-positive list price."""
    # Approximate printing cost for B&W paperback
    # Cost = fixed + per_page
    # For 5.5x8.5 B&W white: $0.85 + $0.012/page
    if paper_type.startswith("bw"):
        printing_cost = 0.85 + 0.012 * page_count
    else:
        printing_cost = 1.00 + 0.07 * page_count  # color is much more expensive
    # Min list = printing_cost / 0.4 (KDP needs 60% > printing, so 60% > printing means
    # list * 0.6 > printing → list > printing / 0.6 — wait actually KDP requires
    # royalty be positive, so list - printing > 0; min where royalty barely positive
    # at 60% rate = printing / 0.6)
    min_list = printing_cost / 0.6
    return printing_cost, min_list


def validate(meta):
    errors = []
    warnings = []
    passed = []

    # Title
    title = meta.get("title", "")
    if not title:
        errors.append("Title is required")
    elif len(title) > TITLE_MAX:
        errors.append(f"Title is {len(title)} chars; max {TITLE_MAX}")
    else:
        passed.append(f"Title: '{title}' ({len(title)} chars)")
        if any(banned in title.lower() for banned in ["free", "bestseller", "#1 in"]):
            warnings.append(f"Title contains promotional language; may be flagged")

    # Subtitle
    subtitle = meta.get("subtitle", "")
    if subtitle:
        if len(subtitle) > SUBTITLE_MAX:
            errors.append(f"Subtitle is {len(subtitle)} chars; max {SUBTITLE_MAX}")
        else:
            passed.append(f"Subtitle: '{subtitle}' ({len(subtitle)} chars)")

    # Description
    desc = meta.get("description", "")
    if not desc:
        errors.append("Description is required")
    elif len(desc) > DESCRIPTION_MAX:
        errors.append(f"Description is {len(desc)} chars; max {DESCRIPTION_MAX}")
    else:
        passed.append(f"Description: {len(desc)} / {DESCRIPTION_MAX} chars")

        # URLs
        urls = check_url_in_description(desc)
        if urls:
            warnings.append(f"Description contains URLs: {urls[:3]}. "
                            "KDP allows only your author website if relevant.")

        # Email
        emails = check_email_in_description(desc)
        if emails:
            errors.append(f"Description contains email addresses: {emails}. "
                          "KDP will reject.")

        # Phone
        phones = check_phone_in_description(desc)
        if phones:
            errors.append(f"Description contains phone numbers: {phones}. "
                          "KDP will reject.")

        # Banned phrases
        for pattern in BANNED_DESCRIPTION_PHRASES:
            matches = re.findall(pattern, desc, re.IGNORECASE)
            if matches:
                warnings.append(f"Description contains potentially problematic "
                                f"phrase: '{matches[0]}'")

        # HTML tags
        found_tags, invalid_tags = check_html_tags_in_description(desc)
        if invalid_tags:
            errors.append(f"Description uses unsupported HTML tags: {invalid_tags}. "
                          f"Allowed: {', '.join(sorted(ALLOWED_HTML_TAGS))}")
        elif found_tags:
            passed.append(f"HTML tags used: {found_tags} (all allowed)")

    # Keywords
    keywords = meta.get("keywords", [])
    if not keywords:
        warnings.append("No keywords specified. KDP allows up to 7; missing them "
                        "reduces discoverability.")
    else:
        if len(keywords) > KEYWORD_MAX_COUNT:
            errors.append(f"{len(keywords)} keywords; KDP allows max {KEYWORD_MAX_COUNT}")
        for kw in keywords:
            if len(kw) > KEYWORD_MAX_LENGTH:
                errors.append(f"Keyword '{kw}' is {len(kw)} chars; max {KEYWORD_MAX_LENGTH}")
            for banned in BANNED_KEYWORD_TERMS:
                if banned in kw.lower():
                    errors.append(f"Keyword '{kw}' contains banned term '{banned}'")
        if len(errors) == 0:
            passed.append(f"Keywords: {len(keywords)}/7 used, all within length limits")

    # Categories
    categories = meta.get("categories", [])
    if not categories:
        warnings.append("No categories specified. KDP requires categories for "
                        "discoverability; pick 2-3.")
    elif len(categories) > 3:
        warnings.append(f"{len(categories)} categories listed; KDP paperback "
                        "allows 3 max via the upload form (more via post-publish "
                        "Browse Categories request).")
    else:
        passed.append(f"Categories: {len(categories)} chosen")

    # ISBN
    isbn = meta.get("isbn", "")
    if isbn:
        # Strip dashes for validation
        isbn_clean = re.sub(r'[-\s]', '', isbn)
        if len(isbn_clean) == 13 and isbn_clean.isdigit():
            passed.append(f"ISBN: {isbn} (13-digit, valid format)")
        elif len(isbn_clean) == 10:
            warnings.append(f"ISBN-10 detected ({isbn}). KDP accepts but ISBN-13 "
                            "preferred. Convert or use ISBN-13 from Bowker.")
        else:
            errors.append(f"ISBN format invalid: '{isbn}'. Should be 13-digit "
                          "(e.g., 978-X-XXXXXXX-X-X)")

    # Pricing
    price = meta.get("price_usd")
    page_count = meta.get("page_count")
    paper_type = meta.get("paper_type", "bw_white")

    if price is not None and page_count is not None:
        printing_cost, min_list = check_min_price(page_count, paper_type)
        if price < min_list:
            errors.append(f"USD list price ${price:.2f} below royalty-positive minimum "
                          f"${min_list:.2f} (printing cost ${printing_cost:.2f}). "
                          "Royalty would be negative.")
        else:
            royalty = (price * 0.6) - printing_cost
            passed.append(f"Price ${price:.2f} → estimated royalty per sale: "
                          f"${royalty:.2f} (printing cost ${printing_cost:.2f})")

    return {"errors": errors, "warnings": warnings, "passed": passed,
            "status": "FAIL" if errors else ("WARN" if warnings else "PASS")}


def main():
    p = argparse.ArgumentParser(description="Validate KDP metadata")
    p.add_argument("path", help="Path to metadata.json")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    with open(args.path) as f:
        meta = json.load(f)

    result = validate(meta)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n=== KDP Metadata Validation: {args.path} ===\n")
        if result["errors"]:
            print(f"❌ ERRORS ({len(result['errors'])}):")
            for e in result["errors"]: print(f"   • {e}")
            print()
        if result["warnings"]:
            print(f"⚠️  WARNINGS ({len(result['warnings'])}):")
            for w in result["warnings"]: print(f"   • {w}")
            print()
        if result["passed"]:
            print(f"✓ PASSED ({len(result['passed'])}):")
            for ok in result["passed"]: print(f"   • {ok}")
            print()
        print(f"=== STATUS: {result['status']} ===\n")

    sys.exit(0 if result["status"] == "PASS" else (1 if result["status"] == "WARN" else 2))


if __name__ == "__main__":
    main()
